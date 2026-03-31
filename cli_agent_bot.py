#!/usr/bin/env python3
"""
CLI Agent Bot — standalone Telegram bot for remote VPS control.

Updated for RealizeOS systemd deployment at /opt/realizeos/.
Provides Claude Code CLI, Gemini CLI, and system management commands.

Security:
- asyncio.create_subprocess_exec (not shell=True)
- Git commands restricted to allowlisted subcommands
- /config masks sensitive values
- All handlers check AUTHORIZED_USERS

Usage:
    python cli_agent_bot.py
"""
import asyncio
import logging
import os
import shutil
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Load .env from the data root (not engine dir)
_env_path = Path("/opt/realizeos/.env")
if _env_path.exists():
    load_dotenv(_env_path, override=True)

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("cli-agent")

# ---------------------------------------------------------------------------
# Configuration (standalone — no old config.py dependency)
# ---------------------------------------------------------------------------
CLI_AGENT_BOT_TOKEN = os.getenv("CLI_AGENT_BOT_TOKEN", "")
KB_PATH = Path(os.getenv("KB_PATH", "/opt/realizeos"))
ENGINE_PATH = Path("/opt/realizeos/engine")
DATA_PATH = Path(os.getenv("DATA_PATH", "/opt/realizeos/data"))

_auth_raw = os.getenv("AUTHORIZED_USERS", "")
AUTHORIZED_USERS: set[int] = set()
for _part in _auth_raw.replace(",", " ").split():
    try:
        AUTHORIZED_USERS.add(int(_part.strip()))
    except ValueError:
        pass

# CLI availability
CLAUDE_CLI_PATH = shutil.which("claude") or "claude"
GEMINI_CLI_PATH = shutil.which("gemini") or "gemini"
CLAUDE_CLI_AVAILABLE = shutil.which("claude") is not None
GEMINI_CLI_AVAILABLE = shutil.which("gemini") is not None
CLI_DEFAULT_TIMEOUT = int(os.getenv("CLI_DEFAULT_TIMEOUT", "120"))
CLI_MAX_CONCURRENT = int(os.getenv("CLI_MAX_CONCURRENT", "2"))

# RealizeOS systemd services
REALIZEOS_SERVICES = ["realizeos-api", "realizeos-sufz", "realizeos-paulo"]

MAX_MSG_LEN = 4000
_semaphore = asyncio.Semaphore(CLI_MAX_CONCURRENT)


# ---------------------------------------------------------------------------
# CLI subprocess wrapper
# ---------------------------------------------------------------------------
@dataclass
class CLIResult:
    output: str
    exit_code: int
    duration_ms: int
    cli: str
    error: str = ""


async def _run_cli(
    cmd_list: list[str], timeout: int, cli_name: str, cwd: str | None = None
) -> CLIResult:
    t0 = time.time()
    async with _semaphore:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_list,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            duration_ms = int((time.time() - t0) * 1000)
            out = stdout.decode("utf-8", errors="replace").strip()
            err = stderr.decode("utf-8", errors="replace").strip()
            if proc.returncode != 0:
                return CLIResult(
                    output=out,
                    exit_code=proc.returncode,
                    duration_ms=duration_ms,
                    cli=cli_name,
                    error=err or out,
                )
            return CLIResult(
                output=out or "(no output)",
                exit_code=0,
                duration_ms=duration_ms,
                cli=cli_name,
            )
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - t0) * 1000)
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            return CLIResult(
                output="",
                exit_code=-1,
                duration_ms=duration_ms,
                cli=cli_name,
                error=f"Timed out after {timeout}s",
            )
        except Exception as e:
            duration_ms = int((time.time() - t0) * 1000)
            return CLIResult(
                output="",
                exit_code=-1,
                duration_ms=duration_ms,
                cli=cli_name,
                error=str(e),
            )


async def call_claude_cli(
    prompt: str, system_prompt: str | None = None, cwd: str | None = None
) -> CLIResult:
    if not CLAUDE_CLI_AVAILABLE:
        return CLIResult(
            output="",
            exit_code=-1,
            duration_ms=0,
            cli="claude",
            error="Claude CLI not installed",
        )
    cmd = [CLAUDE_CLI_PATH, "-p", prompt]
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])
    return await _run_cli(cmd, timeout=CLI_DEFAULT_TIMEOUT, cli_name="claude", cwd=cwd)


async def call_gemini_cli(prompt: str) -> CLIResult:
    if not GEMINI_CLI_AVAILABLE:
        return CLIResult(
            output="",
            exit_code=-1,
            duration_ms=0,
            cli="gemini",
            error="Gemini CLI not installed",
        )
    cmd = [GEMINI_CLI_PATH, "-p", prompt]
    return await _run_cli(cmd, timeout=60, cli_name="gemini")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _is_authorized(update: Update) -> bool:
    if not AUTHORIZED_USERS:
        return False
    return update.effective_user.id in AUTHORIZED_USERS


async def _send_chunked(update: Update, text: str, prefix: str = ""):
    if prefix:
        text = f"{prefix}\n\n{text}"
    if not text.strip():
        text = "(empty output)"
    chunks: list[str] = []
    while text:
        if len(text) <= MAX_MSG_LEN:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, MAX_MSG_LEN)
        if split_at == -1:
            split_at = MAX_MSG_LEN
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    for i, chunk in enumerate(chunks):
        header = f"[{i + 1}/{len(chunks)}]\n" if len(chunks) > 1 else ""
        await update.message.reply_text(f"{header}{chunk}")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Not authorized.")
        return
    lines = [
        "CLI Agent Bot (RealizeOS)",
        "",
        "Commands:",
        "/cli <prompt> — Claude Code CLI",
        "/gemini <prompt> — Gemini CLI",
        "/status — System resources & services",
        "/logs [service] [n] — Service logs via journalctl",
        "/git <cmd> — Git operations (engine repo)",
        "/deploy — Pull + install deps + restart services",
        "/restart [service] — Restart RealizeOS services",
        "/health — API health check",
        "/services — List all RealizeOS services",
        "/config <key> [val] — View/set .env config",
        "",
        f"Claude CLI: {'available' if CLAUDE_CLI_AVAILABLE else 'not installed'}",
        f"Gemini CLI: {'available' if GEMINI_CLI_AVAILABLE else 'not installed'}",
        f"Engine: {ENGINE_PATH}",
        f"KB: {KB_PATH}",
    ]
    await update.message.reply_text("\n".join(lines))


async def cmd_cli(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    prompt = " ".join(context.args) if context.args else ""
    if not prompt:
        await update.message.reply_text("Usage: /cli <prompt>")
        return
    msg = await update.message.reply_text("Running claude CLI...")
    result = await call_claude_cli(prompt, cwd=str(KB_PATH))
    status = "OK" if result.exit_code == 0 else f"Error (exit {result.exit_code})"
    header = f"[claude] {status} ({result.duration_ms}ms)"
    text = result.output if result.exit_code == 0 else result.error
    await _send_chunked(update, text, prefix=header)
    try:
        await msg.delete()
    except Exception:
        pass


async def cmd_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    prompt = " ".join(context.args) if context.args else ""
    if not prompt:
        await update.message.reply_text("Usage: /gemini <prompt>")
        return
    msg = await update.message.reply_text("Running gemini CLI...")
    result = await call_gemini_cli(prompt)
    status = "OK" if result.exit_code == 0 else f"Error (exit {result.exit_code})"
    header = f"[gemini] {status} ({result.duration_ms}ms)"
    text = result.output if result.exit_code == 0 else result.error
    await _send_chunked(update, text, prefix=header)
    try:
        await msg.delete()
    except Exception:
        pass


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    # All static strings — no user input interpolated
    proc = await asyncio.create_subprocess_exec(
        "bash", "-c",
        "echo '=== CPU ===' && nproc && uptime && echo && "
        "echo '=== RAM ===' && free -h && echo && "
        "echo '=== DISK ===' && df -h / && echo && "
        "echo '=== RealizeOS Services ===' && "
        "for svc in realizeos-api realizeos-sufz realizeos-paulo cli-agent-bot; do "
        "status=$(systemctl is-active $svc 2>/dev/null || echo 'not found'); "
        "echo \"  $svc: $status\"; "
        "done && echo && "
        "echo '=== Docker (infra) ===' && "
        "docker stats --no-stream --format "
        "'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}' "
        "2>/dev/null || echo 'docker not available'",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()
    await _send_chunked(update, output or err or "(no output)")


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    args = list(context.args) if context.args else []

    # Parse: /logs [service_name] [num_lines]
    service = "realizeos-sufz"  # default
    n = 50
    valid_services = {
        "api": "realizeos-api",
        "sufz": "realizeos-sufz",
        "paulo": "realizeos-paulo",
        "cli": "cli-agent-bot",
        "realizeos-api": "realizeos-api",
        "realizeos-sufz": "realizeos-sufz",
        "realizeos-paulo": "realizeos-paulo",
    }

    for arg in args:
        if arg in valid_services:
            service = valid_services[arg]
        else:
            try:
                n = min(int(arg), 200)
            except ValueError:
                pass

    proc = await asyncio.create_subprocess_exec(
        "journalctl",
        "-u",
        service,
        "--no-pager",
        "-n",
        str(n),
        "--output=short",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = (
        stdout.decode("utf-8", errors="replace").strip()
        or stderr.decode("utf-8", errors="replace").strip()
    )
    await _send_chunked(
        update, output or "No logs found", prefix=f"Last {n} lines - {service}"
    )


async def cmd_git(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    args = list(context.args) if context.args else ["status"]
    subcmd = args[0]
    safe_commands = {"status", "log", "diff", "branch", "remote", "show", "stash"}
    if subcmd not in safe_commands:
        await update.message.reply_text(
            f"Safe git commands only: {', '.join(sorted(safe_commands))}"
        )
        return
    cmd_list = ["git", "-C", str(ENGINE_PATH)] + args
    proc = await asyncio.create_subprocess_exec(
        *cmd_list,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = stdout.decode("utf-8", errors="replace").strip()
    if proc.returncode != 0:
        output = stderr.decode("utf-8", errors="replace").strip() or output
    await _send_chunked(update, output or "(no output)", prefix=f"git {subcmd}")


async def cmd_deploy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    msg = await update.message.reply_text("Deploying: git pull...")

    # Step 1: git pull
    proc = await asyncio.create_subprocess_exec(
        "git", "-C", str(ENGINE_PATH), "pull", "--rebase", "origin", "main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    pull_output = stdout.decode("utf-8", errors="replace").strip()
    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()
        await update.message.reply_text(f"Git pull failed:\n{err}")
        return

    await msg.edit_text("Git pull OK. Installing dependencies...")

    # Step 2: pip install
    proc = await asyncio.create_subprocess_exec(
        "/opt/realizeos/.venv/bin/pip",
        "install", "-r", str(ENGINE_PATH / "requirements.txt"), "-q",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    pip_ok = proc.returncode == 0

    await msg.edit_text("Dependencies updated. Restarting services...")

    # Step 3: restart services
    results = []
    for svc in REALIZEOS_SERVICES:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "restart", svc,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        status_icon = "OK" if proc.returncode == 0 else "FAIL"
        results.append(f"  {status_icon} {svc}")

    await update.message.reply_text(
        f"Deploy complete!\n\n"
        f"Pull: {pull_output}\n"
        f"Deps: {'OK' if pip_ok else 'warnings'}\n\n"
        f"Services:\n" + "\n".join(results)
    )


async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    args = list(context.args) if context.args else []

    valid_services = {
        "api": "realizeos-api",
        "sufz": "realizeos-sufz",
        "paulo": "realizeos-paulo",
        "realizeos-api": "realizeos-api",
        "realizeos-sufz": "realizeos-sufz",
        "realizeos-paulo": "realizeos-paulo",
        "all": "all",
    }

    if args and args[0] in valid_services:
        if args[0] == "all":
            services_to_restart = REALIZEOS_SERVICES
        else:
            services_to_restart = [valid_services[args[0]]]
    else:
        services_to_restart = REALIZEOS_SERVICES  # default: restart all

    results = []
    for svc in services_to_restart:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "restart", svc,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode == 0:
            results.append(f"OK - {svc} restarted")
        else:
            err = stderr.decode("utf-8", errors="replace").strip()
            results.append(f"FAIL - {svc}: {err}")

    await update.message.reply_text("\n".join(results))


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    port = os.getenv("REALIZE_PORT", "8082")
    proc = await asyncio.create_subprocess_exec(
        "curl", "-s", "-m", "5", f"http://localhost:{port}/health",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = stdout.decode("utf-8", errors="replace").strip()
    if proc.returncode == 0 and output:
        await update.message.reply_text(f"API Health:\n{output}")
    else:
        err = stderr.decode("utf-8", errors="replace").strip()
        await update.message.reply_text(f"API unreachable:\n{err or 'no response'}")


async def cmd_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    all_services = REALIZEOS_SERVICES + ["cli-agent-bot"]
    lines = ["RealizeOS Services:"]
    for svc in all_services:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "is-active", svc,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        status = stdout.decode().strip()
        icon = "OK" if status == "active" else "XX"
        lines.append(f"  [{icon}] {svc}: {status}")

    # Also show Docker infra
    lines.append("\nInfra (Docker):")
    proc = await asyncio.create_subprocess_exec(
        "docker", "ps", "--format", "table {{.Names}}\t{{.Status}}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    docker_out = stdout.decode("utf-8", errors="replace").strip()
    lines.append(docker_out or "  (no containers)")

    await _send_chunked(update, "\n".join(lines))


async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    args = context.args or []
    env_file = Path("/opt/realizeos/.env")

    if not args:
        if env_file.exists():
            keys = []
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    keys.append(line.split("=", 1)[0])
            await _send_chunked(update, "\n".join(keys), prefix=".env keys")
        else:
            await update.message.reply_text(".env file not found")
        return

    key = args[0].upper()
    if len(args) == 1:
        val = os.getenv(key, "(not set)")
        sensitive = ("token", "key", "secret", "password", "pat")
        if any(s in key.lower() for s in sensitive):
            val = val[:4] + "..." + val[-4:] if len(val) > 8 else "****"
        await update.message.reply_text(f"{key} = {val}")
        return

    new_val = " ".join(args[1:])
    if not env_file.exists():
        await update.message.reply_text(".env file not found")
        return
    lines = env_file.read_text().splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={new_val}"
            found = True
            break
    if not found:
        lines.append(f"{key}={new_val}")
    env_file.write_text("\n".join(lines) + "\n")
    await update.message.reply_text(f"Updated {key}. Use /restart to apply.")


async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    message = update.message.text
    if not message or not message.strip():
        return
    msg = await update.message.reply_text("Thinking via Claude CLI...")
    result = await call_claude_cli(
        prompt=message,
        system_prompt=(
            "You are a helpful VPS management assistant for a RealizeOS deployment. "
            "Respond concisely."
        ),
        cwd=str(KB_PATH),
    )
    text = result.output if result.exit_code == 0 else f"Error: {result.error}"
    await _send_chunked(update, text)
    try:
        await msg.delete()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------
async def post_init(app: Application):
    commands = [
        BotCommand("start", "Show help"),
        BotCommand("cli", "Run Claude Code CLI"),
        BotCommand("gemini", "Run Gemini CLI"),
        BotCommand("status", "System resources & services"),
        BotCommand("logs", "Service logs [service] [lines]"),
        BotCommand("git", "Git operations on engine"),
        BotCommand("deploy", "Pull + deps + restart"),
        BotCommand("restart", "Restart services [service|all]"),
        BotCommand("health", "API health check"),
        BotCommand("services", "List all services"),
        BotCommand("config", "View/set .env config"),
    ]
    await app.bot.set_my_commands(commands)
    logger.info("Bot commands menu registered")


async def run():
    if not CLI_AGENT_BOT_TOKEN:
        logger.error("CLI_AGENT_BOT_TOKEN not set")
        return

    app = (
        Application.builder().token(CLI_AGENT_BOT_TOKEN).post_init(post_init).build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("cli", cmd_cli))
    app.add_handler(CommandHandler("gemini", cmd_gemini))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CommandHandler("git", cmd_git))
    app.add_handler(CommandHandler("deploy", cmd_deploy))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(CommandHandler("services", cmd_services))
    app.add_handler(CommandHandler("config", cmd_config))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text)
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES, drop_pending_updates=True
    )
    logger.info("[OK] CLI Agent Bot started (RealizeOS mode)")
    logger.info(f"  Engine: {ENGINE_PATH}")
    logger.info(f"  KB: {KB_PATH}")
    logger.info(f"  Claude CLI: {'available' if CLAUDE_CLI_AVAILABLE else 'NOT available'}")
    logger.info(f"  Gemini CLI: {'available' if GEMINI_CLI_AVAILABLE else 'NOT available'}")

    stop_event = asyncio.Event()

    def _shutdown(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        stop_event.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    await stop_event.wait()

    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    logger.info("[STOP] CLI Agent Bot stopped")


if __name__ == "__main__":
    asyncio.run(run())
