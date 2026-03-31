#!/usr/bin/env python3
"""
RealizeOS CLI — Initialize, serve, and manage your AI operations system.

Usage:
    python cli.py init [--template NAME]       Create a new system from a template
    python cli.py init --setup setup.yaml      Create system from a setup file
    python cli.py serve [--port PORT]          Start the API server
    python cli.py bot                          Start the Telegram bot
    python cli.py status                       Show system status
    python cli.py index                        Rebuild the KB search index
    python cli.py venture create               Create a new venture
    python cli.py venture delete               Delete a venture
    python cli.py venture list                 List all ventures
"""

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

# Load .env automatically for non-Docker users
try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("realize")

# .gitignore content for new projects
_GITIGNORE_CONTENT = """\
# Secrets — never commit these
.env
setup.yaml

# Data
data/
*.db

# Python
__pycache__/
*.pyc
.venv/
venv/

# OS
.DS_Store
Thumbs.db

# Credentials
.credentials/
"""


def _parse_authorized_users(value) -> set[int]:
    """Normalize configured Telegram user IDs into a set of integers."""
    if not value:
        return set()

    if isinstance(value, str):
        items = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]

    authorized = set()
    for item in items:
        try:
            authorized.add(int(item))
        except (TypeError, ValueError):
            logger.warning("Ignoring invalid authorized Telegram user ID: %r", item)
    return authorized


def _init_from_setup_file(setup_path: Path, target_dir: Path):
    """
    Initialize RealizeOS from a setup.yaml file.

    Reads API keys and business info, then:
    1. Generates .env from the API key values
    2. Copies the chosen template → realize-os.yaml with business name
    3. Copies realize_lite/ FABRIC structure
    4. Pre-populates venture-identity.md
    5. Creates .gitignore
    """
    import yaml

    if not setup_path.exists():
        print(f"Error: Setup file not found: {setup_path}")
        sys.exit(1)

    with open(setup_path, encoding="utf-8") as f:
        setup = yaml.safe_load(f)

    if not setup:
        print("Error: Setup file is empty or invalid YAML.")
        sys.exit(1)

    # Extract values
    anthropic_key = setup.get("anthropic_api_key", "")
    google_key = setup.get("google_ai_api_key", "")
    template_name = setup.get("template", "consulting")
    business_name = setup.get("business_name", "My Business")
    business_desc = setup.get("business_description", "")

    # Optional overrides
    realize_port = setup.get("realize_port", "8080")
    realize_api_key = setup.get("realize_api_key", "")
    openai_key = setup.get("openai_api_key", "")
    telegram_token = setup.get("telegram_bot_token", "")
    brave_key = setup.get("brave_api_key", "")

    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate .env
    env_dest = target_dir / ".env"
    if not env_dest.exists():
        env_lines = [
            "# RealizeOS Environment — generated from setup.yaml",
            f"ANTHROPIC_API_KEY={anthropic_key}",
            f"GOOGLE_AI_API_KEY={google_key}",
            "",
            "REALIZE_HOST=127.0.0.1",
            f"REALIZE_PORT={realize_port}",
            f"REALIZE_API_KEY={realize_api_key}",
            "CORS_ORIGINS=*",
            "",
            "KB_PATH=.",
            "DATA_PATH=./data",
            "REALIZE_CONFIG=realize-os.yaml",
            "",
            "BROWSER_ENABLED=false",
            "MCP_ENABLED=false",
            "",
            "RATE_LIMIT_PER_MINUTE=30",
            "COST_LIMIT_PER_HOUR_USD=5.00",
        ]
        # Add optional keys only if provided
        if openai_key:
            env_lines.append(f"OPENAI_API_KEY={openai_key}")
        if telegram_token:
            env_lines.append(f"TELEGRAM_BOT_TOKEN={telegram_token}")
        if brave_key:
            env_lines.append(f"BRAVE_API_KEY={brave_key}")

        env_dest.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
        print("  ✓ Created .env with your API keys")
    else:
        print("  • .env already exists, skipping")

    # 2. Copy template → realize-os.yaml with business name
    templates_dir = Path(__file__).parent / "templates"
    template_file = templates_dir / f"{template_name}.yaml"
    if not template_file.exists():
        available = [f.stem for f in templates_dir.glob("*.yaml") if not f.stem.startswith("_")]
        print(f"Error: Template '{template_name}' not found. Available: {', '.join(available)}")
        sys.exit(1)

    config_dest = target_dir / "realize-os.yaml"
    if not config_dest.exists():
        # Read template and substitute business name
        content = template_file.read_text(encoding="utf-8")
        content = content.replace("My Consulting Practice", business_name)
        content = content.replace("Consulting Practice", business_name)
        config_dest.write_text(content, encoding="utf-8")
        print(f"  ✓ Created realize-os.yaml from '{template_name}' template")
    else:
        print("  • realize-os.yaml already exists, skipping")

    # 3. Copy FABRIC structure from realize_lite
    lite_src = Path(__file__).parent / "realize_lite"
    if lite_src.exists():
        copied = 0
        for item in lite_src.rglob("*"):
            if item.is_file() and ".obsidian" not in str(item):
                relative = item.relative_to(lite_src)
                dest = target_dir / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copy2(item, dest)
                    copied += 1
        print(f"  ✓ Created FABRIC structure ({copied} files)")
    else:
        print("  ⚠ realize_lite directory not found, skipping FABRIC copy")

    # 4. Pre-populate venture-identity.md
    # Find the system directory from the template (e.g., systems/my-business-1)
    brand_files = list(target_dir.rglob("venture-identity.md"))
    for brand_file in brand_files:
        content = brand_file.read_text(encoding="utf-8")
        # Replace placeholder business name and add description
        if "My Business" in content or "Your Business" in content:
            content = content.replace("My Business", business_name)
            content = content.replace("Your Business", business_name)
            if business_desc and "business_description" not in content:
                content = content.replace(
                    "# Venture Identity",
                    f"# Venture Identity\n\n> {business_desc}",
                )
            brand_file.write_text(content, encoding="utf-8")
            print(f"  ✓ Pre-populated {brand_file.relative_to(target_dir)} with business info")

    # 5. Create .gitignore
    gitignore_dest = target_dir / ".gitignore"
    if not gitignore_dest.exists():
        gitignore_dest.write_text(_GITIGNORE_CONTENT, encoding="utf-8")
        print("  ✓ Created .gitignore")

    # 6. Copy .env.example
    env_example_src = Path(__file__).parent / ".env.example"
    env_example_dest = target_dir / ".env.example"
    if env_example_src.exists() and not env_example_dest.exists():
        shutil.copy2(env_example_src, env_example_dest)
        print("  ✓ Copied .env.example")


def cmd_init(args):
    """Initialize a new system from a template or setup file."""
    target_dir = Path(args.directory or ".")

    # Setup file mode: reads setup.yaml and configures everything
    if args.setup:
        setup_path = Path(args.setup)
        print(f"Initializing RealizeOS from {setup_path}...")
        _init_from_setup_file(setup_path, target_dir)
        print()
        print("Initialization complete!")
        print()
        print("Next steps:")
        print("  1. Review and customize your venture identity:")
        print("     Edit systems/*/F-foundations/venture-identity.md")
        print("  2. Start the server:")
        print("     python cli.py serve")
        print("  3. Or deploy with Docker:")
        print("     docker compose up --build")
        return

    # Template mode (original flow, enhanced)
    template_name = args.template or "consulting"

    templates_dir = Path(__file__).parent / "templates"
    template_file = templates_dir / f"{template_name}.yaml"

    if not template_file.exists():
        available = [f.stem for f in templates_dir.glob("*.yaml") if not f.stem.startswith("_")]
        print(f"Template '{template_name}' not found.")
        print(f"Available: {', '.join(available)}")
        sys.exit(1)

    # Copy the Lite vault structure as a starting point
    lite_src = Path(__file__).parent / "realize_lite"
    if not lite_src.exists():
        print("Error: realize_lite directory not found.")
        sys.exit(1)

    # Create target if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy vault structure
    for item in lite_src.rglob("*"):
        if item.is_file() and ".obsidian" not in str(item):
            relative = item.relative_to(lite_src)
            dest = target_dir / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(item, dest)

    # Copy template config
    config_dest = target_dir / "realize-os.yaml"
    if not config_dest.exists():
        shutil.copy2(template_file, config_dest)

    # Copy .env.example
    env_example = Path(__file__).parent / ".env.example"
    env_dest = target_dir / ".env.example"
    if env_example.exists() and not env_dest.exists():
        shutil.copy2(env_example, env_dest)

    # Auto-create .env from .env.example (so users don't need cp/copy)
    env_file = target_dir / ".env"
    env_example_local = target_dir / ".env.example"
    if not env_file.exists() and env_example_local.exists():
        shutil.copy2(env_example_local, env_file)
        print("  ✓ Created .env from .env.example — edit it to add your API keys")

    # Create .gitignore
    gitignore_dest = target_dir / ".gitignore"
    if not gitignore_dest.exists():
        gitignore_dest.write_text(_GITIGNORE_CONTENT, encoding="utf-8")

    print(f"Initialized RealizeOS with '{template_name}' template at {target_dir.resolve()}")
    print()
    print("Next steps:")
    print("  1. Edit .env and add your API keys")
    print(f"  2. Edit {config_dest} to configure your system")
    print("  3. Fill in your venture identity and agent definitions")
    print("  4. Run: python cli.py serve")


def cmd_serve(args):
    """Start the API server."""
    host = args.host or os.environ.get("REALIZE_HOST", "127.0.0.1")
    port = int(args.port or os.environ.get("REALIZE_PORT", "8080"))

    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)

    print(f"Starting RealizeOS API on {host}:{port}")
    uvicorn.run(
        "realize_api.main:app",
        host=host,
        port=port,
        reload=args.reload,
        log_level="info",
    )


def _resolve_token(raw_token: str) -> str:
    """Resolve a bot token — supports ${ENV_VAR} syntax."""
    if raw_token and raw_token.startswith("${") and raw_token.endswith("}"):
        env_var = raw_token[2:-1]
        return os.environ.get(env_var, "")
    return raw_token


def _build_telegram_channel(telegram_config: dict):
    """Build a TelegramChannel from a channel config dict."""
    from realize_core.channels.telegram import TelegramChannel

    token = _resolve_token(telegram_config.get("token", ""))
    if not token:
        name = telegram_config.get("name", "unnamed")
        print(f"Warning: No token for Telegram bot '{name}'. Check .env")
        return None

    return TelegramChannel(
        bot_token=token,
        system_key=telegram_config.get("system_key", ""),
        authorized_users=_parse_authorized_users(telegram_config.get("authorized_users", [])),
        mode=telegram_config.get("mode", "single"),
        name=telegram_config.get("name", ""),
        topic_routing=telegram_config.get("topic_routing", {}),
    )


def cmd_bot(args):
    """Start Telegram bot(s). Use --name to start a specific bot."""
    import asyncio

    async def run_bot():
        from realize_core.config import load_config

        config = load_config()
        channels = config.get("channels", [])

        # Find telegram channel(s)
        telegram_configs = [ch for ch in channels if ch.get("type") == "telegram"]
        if not telegram_configs:
            print("No Telegram channel configured in realize-os.yaml")
            sys.exit(1)

        bot_name = getattr(args, "name", None)

        if bot_name:
            # Start a specific bot by name
            target = None
            for ch in telegram_configs:
                if ch.get("name") == bot_name:
                    target = ch
                    break
            if not target:
                available = [ch.get("name", "unnamed") for ch in telegram_configs]
                print(f"Bot '{bot_name}' not found. Available: {', '.join(available)}")
                sys.exit(1)

            channel = _build_telegram_channel(target)
            if not channel:
                sys.exit(1)

            desc = target.get("description", bot_name)
            print(f"Starting Telegram bot: {desc}")
            await channel.start()
            print(f"Bot '{bot_name}' is running. Press Ctrl+C to stop.")

            stop_event = asyncio.Event()
            try:
                await stop_event.wait()
            except asyncio.CancelledError:
                pass
            finally:
                await channel.stop()
        else:
            # Start ALL telegram bots concurrently
            bots = []
            for ch in telegram_configs:
                channel = _build_telegram_channel(ch)
                if channel:
                    bots.append((ch.get("name", "unnamed"), channel))

            if not bots:
                print("No valid Telegram bots could be initialized.")
                sys.exit(1)

            for name, channel in bots:
                print(f"Starting bot: {name}...")
                await channel.start()
                print(f"  Bot '{name}' started.")

            print(f"\n{len(bots)} bot(s) running. Press Ctrl+C to stop.")

            stop_event = asyncio.Event()
            try:
                await stop_event.wait()
            except asyncio.CancelledError:
                pass
            finally:
                for name, channel in bots:
                    await channel.stop()

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\nTelegram bot(s) stopped.")


def cmd_status(args):
    """Show system status."""
    from pathlib import Path

    from realize_core.config import KB_PATH, build_systems_dict, is_env_true, load_config

    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    kb_path = Path(config.get("kb_path", KB_PATH)).resolve()
    systems = build_systems_dict(config, kb_path=kb_path)

    print("RealizeOS Status")
    print("=" * 40)
    print(f"Systems: {len(systems)}")

    for key, sys_config in systems.items():
        agents = list(sys_config.get("agents", {}).keys())
        print(f"\n  {key} ({sys_config.get('name', key)})")
        print(f"    Agents: {', '.join(agents) if agents else 'none'}")
        routing = sys_config.get("routing", {})
        if routing:
            print(f"    Pipelines: {', '.join(routing.keys())}")

    # Check API keys
    print("\nLLM Providers:")
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("  Anthropic: configured")
    else:
        print("  Anthropic: NOT configured")
    if os.environ.get("GOOGLE_AI_API_KEY"):
        print("  Google AI: configured")
    else:
        print("  Google AI: NOT configured")

    # Check tools
    print("\nTools:")
    print(f"  Web Search: {'configured' if os.environ.get('BRAVE_API_KEY') else 'not configured'}")
    print(f"  Browser: {'enabled' if is_env_true('BROWSER_ENABLED', default=False) else 'disabled'}")
    print(f"  MCP: {'enabled' if is_env_true('MCP_ENABLED', default=False) else 'disabled'}")


def cmd_index(args):
    """Rebuild the KB search index."""
    from realize_core.config import load_config

    config = load_config()
    kb_path = config.get("kb_path", ".")

    from realize_core.kb.indexer import index_kb_files

    count = index_kb_files(kb_path, force=True)
    print(f"Indexed {count} files from {kb_path}")


def cmd_evolve(args):
    """Run gap analysis and suggest system improvements."""
    import asyncio

    from realize_core.memory.store import init_db

    init_db()

    try:
        from realize_core.evolution.analytics import init_analytics_tables
        init_analytics_tables()
    except Exception:
        pass

    async def _run():
        from realize_core.evolution.gap_detector import (
            format_suggestions_overview,
            get_pending_suggestions,
            run_gap_analysis,
        )

        print("Running gap analysis on recent interactions...")
        new_suggestions = await run_gap_analysis(days=7)
        if new_suggestions:
            print(f"\nFound {len(new_suggestions)} new suggestion(s):")
            for s in new_suggestions:
                print(f"  - [{s['type']}] {s['title']}")

        all_pending = get_pending_suggestions()
        if all_pending:
            print(f"\n{format_suggestions_overview(all_pending)}")
        else:
            print("\nNo pending evolution suggestions. System is running well.")

    asyncio.run(_run())


def cmd_maintain(args):
    """Run database maintenance (VACUUM, ANALYZE) on memory and KB databases."""
    from realize_core.memory.store import init_db, maintenance

    print("Running database maintenance...")
    init_db()
    maintenance()

    # Also maintain KB index database if it exists
    from realize_core.config import KB_PATH

    kb_db = KB_PATH / "kb_index.db"
    if kb_db.exists():
        import sqlite3

        try:
            conn = sqlite3.connect(str(kb_db))
            conn.execute("ANALYZE")
            conn.close()
            conn = sqlite3.connect(str(kb_db))
            conn.execute("VACUUM")
            conn.close()
            print(f"KB index maintenance complete: {kb_db}")
        except Exception as e:
            print(f"KB index maintenance failed: {e}")

    print("Maintenance complete.")


def cmd_venture(args):
    """Manage ventures (create, delete, list)."""
    from realize_core.scaffold import delete_venture, list_ventures, scaffold_venture

    project_root = Path(args.directory or ".")

    if args.venture_action == "create":
        if not args.key:
            print("Error: --key is required for venture create")
            sys.exit(1)
        try:
            stats = scaffold_venture(
                project_root=project_root,
                key=args.key,
                name=args.name or "",
                description=args.description or "",
            )
            print(f"Created venture '{args.key}' at systems/{args.key}/")
            print(f"  {stats['dirs_created']} directories, {stats['files_created']} files")
            print("\nThe venture has been added to realize-os.yaml.")
            print(f"Next: customize systems/{args.key}/F-foundations/venture-identity.md")
        except FileExistsError as e:
            print(f"Error: {e}")
            sys.exit(1)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif args.venture_action == "delete":
        if not args.key:
            print("Error: --key is required for venture delete")
            sys.exit(1)
        confirm = args.confirm or ""
        if confirm != args.key:
            print(f"To delete venture '{args.key}', pass --confirm {args.key}")
            sys.exit(1)
        try:
            delete_venture(project_root, args.key, confirm_name=confirm)
            print(f"Deleted venture '{args.key}' and removed from realize-os.yaml.")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif args.venture_action == "list":
        ventures = list_ventures(project_root)
        if not ventures:
            print("No ventures configured. Run: python cli.py venture create --key my-venture")
            return
        print(f"Ventures ({len(ventures)}):")
        for v in ventures:
            status = "OK" if v["exists"] else "MISSING"
            print(f"  {v['key']} — {v['name']} ({v['directory']}) [{status}]")

    else:
        print("Usage: python cli.py venture {create|delete|list}")
        sys.exit(1)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="RealizeOS — AI Operations System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize a new system")
    init_parser.add_argument("--template", "-t", default="consulting", help="Template name")
    init_parser.add_argument("--setup", "-s", default=None, help="Path to setup.yaml for one-command init")
    init_parser.add_argument("--directory", "-d", default=".", help="Target directory")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default=None, help="Host (default: 127.0.0.1)")
    serve_parser.add_argument("--port", "-p", default=None, help="Port (default: 8080)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # bot
    bot_parser = subparsers.add_parser("bot", help="Start Telegram bot(s)")
    bot_parser.add_argument("--name", "-n", default=None, help="Start a specific bot by name (e.g., sufz, paulo)")

    # status
    subparsers.add_parser("status", help="Show system status")

    # index
    subparsers.add_parser("index", help="Rebuild KB search index")

    # evolve
    subparsers.add_parser("evolve", help="Run gap analysis and suggest system improvements")

    # maintain
    subparsers.add_parser("maintain", help="Run database maintenance (VACUUM, ANALYZE)")

    # venture
    venture_parser = subparsers.add_parser("venture", help="Manage ventures")
    venture_parser.add_argument(
        "venture_action", choices=["create", "delete", "list"], help="Action: create, delete, or list"
    )
    venture_parser.add_argument("--key", "-k", help="Venture key (directory name)")
    venture_parser.add_argument("--name", "-n", help="Display name")
    venture_parser.add_argument("--description", help="Venture description")
    venture_parser.add_argument("--directory", "-d", default=".", help="Project root directory")
    venture_parser.add_argument("--confirm", help="Confirm deletion (must match --key)")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "init": cmd_init,
        "serve": cmd_serve,
        "bot": cmd_bot,
        "status": cmd_status,
        "index": cmd_index,
        "evolve": cmd_evolve,
        "maintain": cmd_maintain,
        "venture": cmd_venture,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
