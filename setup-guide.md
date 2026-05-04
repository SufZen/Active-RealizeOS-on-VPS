# RealizeOS VPS — Operator Guide

This guide is for the **active VPS instance** of RealizeOS. It covers bringing the deployment up, running it day-to-day, updating it, and recovering when things go sideways. For the public Lite/Obsidian package see [`docs/lite-guide.md`](docs/lite-guide.md). For the public Full distribution see [`docs/full-guide.md`](docs/full-guide.md).

## Topology

```
VPS (root: /opt/realizeos/)
├── /opt/realizeos/engine/        ← this git repo, deployed code
├── /opt/realizeos/.env           ← real secrets (NOT in git)
├── /opt/realizeos/data/          ← SQLite (memory, sessions, evolution state)
├── /opt/realizeos/.credentials/  ← Google OAuth credentials (optional)
└── systemd units:
    ├── realizeos-api             FastAPI + tools (Docker Compose service `api`)
    ├── realizeos-sufz            Telegram super-agent bot
    ├── realizeos-paulo           Telegram bot pinned to `personal` (Portugal)
    └── realizeos-cli-agent       Standalone cli_agent_bot.py (VPS control)
```

The first three services live inside `docker-compose.yml`; the last runs `cli_agent_bot.py` directly. `realize-os.yaml`, `shared/`, `systems/`, and `data/` are bind-mounted into the API and Telegram containers (`docker-compose.yml:7–11, 41–43`), so editing those files takes effect on the next message — no rebuild required.

## First-Time Bring-Up

You only need this section once per VPS. After that, see [Day-to-Day Operations](#day-to-day-operations).

### 1. Clone the engine

```bash
sudo mkdir -p /opt/realizeos
sudo chown "$USER":"$USER" /opt/realizeos
git clone <this-repo> /opt/realizeos/engine
cd /opt/realizeos/engine
```

### 2. Author `.env`

```bash
cp .env.example /opt/realizeos/.env
# Edit /opt/realizeos/.env with real values.
```

Minimum to get the API running:
- `ANTHROPIC_API_KEY` (or `GOOGLE_AI_API_KEY` — at least one provider)
- `REALIZE_API_KEY` — set a strong shared secret for the REST API
- `AUTHORIZED_USERS` — comma-separated Telegram user IDs that may use the bots

For Telegram bots, also fill:
- `SUFZ_BOT_TOKEN` — super-agent across all 10 systems
- `PAULO_BOT_TOKEN` — Portugal bureaucracy concierge
- `CLI_AGENT_BOT_TOKEN` — VPS-control bot (`cli_agent_bot.py`)

Optional: `BRAVE_API_KEY` (web search), `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (Google Workspace tools), `OPENAI_API_KEY`, `OLLAMA_BASE_URL`, voice keys (`ELEVENLABS_*`, `TWILIO_*`), `MCP_ENABLED`, `BROWSER_ENABLED`.

### 3. Confirm `realize-os.yaml`

This repo ships with the **live** config (10 ventures, real bot routing, voice). On a fresh VPS that should be a one-time review — confirm the ventures, agent rosters, channels, and `voice` section reflect what you actually want this box to run.

### 4. Bring up the API + Telegram services

```bash
cd /opt/realizeos/engine
docker compose up -d --build
```

This starts two containers (`api`, `telegram`) sharing the same image. Bind mounts: `./data`, `./realize-os.yaml` (read-only), `./shared`, `./systems`, `./.credentials`.

Health check (engine container exposes `/health` internally; from the host):

```bash
curl http://localhost:8080/health
# → {"status":"ok"}
```

### 5. Start the standalone CLI Agent bot

`cli_agent_bot.py` is **not** part of `docker-compose.yml`. Run it as its own systemd unit. Example unit file:

```ini
# /etc/systemd/system/realizeos-cli-agent.service
[Unit]
Description=RealizeOS CLI Agent (Telegram VPS control)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/realizeos/engine
ExecStart=/usr/bin/python3 /opt/realizeos/engine/cli_agent_bot.py
EnvironmentFile=/opt/realizeos/.env
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now realizeos-cli-agent
journalctl -u realizeos-cli-agent -f
```

`cli_agent_bot.py` expects `/opt/realizeos/.env` and the engine to be at `/opt/realizeos/engine` (`cli_agent_bot.py:36–53`). It exposes Claude CLI, Gemini CLI, allowlisted git commands, and start/stop/status of the systemd services `realizeos-api`, `realizeos-sufz`, `realizeos-paulo` (`cli_agent_bot.py:73`). Only IDs in `AUTHORIZED_USERS` may use it.

### 6. Smoke test

```bash
# REST API
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $REALIZE_API_KEY" \
  -d '{"message": "Hello", "system_key": "realizeos", "user_id": "operator"}'

# CLI status
docker compose exec api python cli.py status

# Telegram bots — message Sufz, Paulo, and the CLI Agent bot from an authorized account.
```

## Day-to-Day Operations

### Tail logs

```bash
docker compose logs -f api
docker compose logs -f telegram
journalctl -u realizeos-cli-agent -f
```

### Restart services

```bash
docker compose restart api telegram
sudo systemctl restart realizeos-cli-agent
```

### Hot-reload `realize-os.yaml`

Most `realize-os.yaml` changes (agent routing, feature flags, system entries, LLM routing) are picked up via:

```bash
curl -X POST http://localhost:8080/api/systems/reload \
  -H "X-API-Key: $REALIZE_API_KEY"
```

For changes to channels, voice, or anything that affects bot startup, restart the relevant container instead.

### KB index, maintenance, evolution

```bash
docker compose exec api python cli.py status      # System status snapshot
docker compose exec api python cli.py index       # Rebuild KB search index
docker compose exec api python cli.py maintain    # SQLite VACUUM + ANALYZE
docker compose exec api python cli.py evolve      # Generate gap/skill/prompt suggestions
```

Suggestions are queued — they do **not** auto-apply (`evolution_auto_apply: false` in `realize-os.yaml`). Approve / dismiss via the API:

```bash
curl http://localhost:8080/api/evolution/suggestions -H "X-API-Key: $REALIZE_API_KEY"
curl -X POST http://localhost:8080/api/evolution/approve/<id> -H "X-API-Key: $REALIZE_API_KEY"
curl -X POST http://localhost:8080/api/evolution/dismiss/<id> -H "X-API-Key: $REALIZE_API_KEY"
```

### Manage ventures

```bash
docker compose exec api python cli.py venture list
docker compose exec api python cli.py venture create --key new-venture --name "New Venture"
docker compose exec api python cli.py venture delete --key new-venture --confirm new-venture
```

A new venture appears immediately under `systems/<key>/`. Fill `F-foundations/venture-identity.md` and `F-foundations/venture-voice.md` before relying on it.

### Backups

The state that matters lives in three places:
- `/opt/realizeos/data/` — SQLite (memory, sessions, evolution).
- `/opt/realizeos/engine/shared/` — cross-system identity, methods, deal dossiers.
- `/opt/realizeos/engine/systems/` — per-venture FABRIC content.

A simple snapshot:

```bash
sudo tar -czf "realizeos-backup-$(date +%F).tar.gz" \
  -C /opt/realizeos data .env \
  -C /opt/realizeos/engine shared systems realize-os.yaml
```

Move the archive off-box.

## Updating the Deployment

```bash
cd /opt/realizeos/engine
git fetch origin
git pull --ff-only origin main          # or your deployed branch
docker compose build api                # Rebuild image with new code
docker compose up -d                    # Apply
sudo systemctl restart realizeos-cli-agent
```

If schemas changed (rare), check `realize_core/memory/` and `realize_core/security/` migrations, then run `python cli.py maintain` to compact.

## Telegram Bot Management

| Bot | Token env var | What it talks to |
| --- | --- | --- |
| Sufz | `SUFZ_BOT_TOKEN` | All 10 systems via super-agent routing; forum-thread topic IDs map to `system_key` (`realize-os.yaml → channels[sufz].topic_routing`) |
| Paulo | `PAULO_BOT_TOKEN` | Pinned to `system_key: personal` — Portuguese bureaucracy |
| CLI Agent | `CLI_AGENT_BOT_TOKEN` | VPS host (Claude CLI, Gemini CLI, git, systemd services) |

Rotating a token: edit `/opt/realizeos/.env`, then restart:

```bash
docker compose restart telegram          # Sufz + Paulo
sudo systemctl restart realizeos-cli-agent
```

Adding/removing authorized users: edit `AUTHORIZED_USERS` (comma-separated Telegram user IDs), restart the same services. The CLI Agent reads it from `/opt/realizeos/.env` directly.

## Voice Channel (ElevenLabs + Twilio)

`realize-os.yaml → voice` configures outbound calls (Twilio) and the conversational agent (ElevenLabs). Inbound webhooks land at `/webhooks/elevenlabs`. To turn voice off, set `voice.enabled: false` and reload systems. Required env vars: `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`, `ELEVENLABS_PHONE_NUMBER_ID`, `ELEVENLABS_PT_VOICE_ID`, `ELEVENLABS_WEBHOOK_SECRET`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `PT_CALLER_PHONE`.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `/health` 5xx or container restart-looping | `docker compose logs api` — usually a missing env var or a malformed `realize-os.yaml` |
| Bot is silent | `docker compose logs telegram`; confirm `SUFZ_BOT_TOKEN`/`PAULO_BOT_TOKEN` is set; confirm the user's Telegram ID is in `AUTHORIZED_USERS` |
| CLI Agent bot offline | `journalctl -u realizeos-cli-agent -e`; confirm `CLI_AGENT_BOT_TOKEN` and that `/opt/realizeos/.env` is readable by the unit |
| API rejects every request with 401 | Missing `X-API-Key` / `Authorization: Bearer` header, or `REALIZE_API_KEY` mismatch |
| Wrong agent responding | Check `realize-os.yaml → systems[<key>].agent_routing`; reload via `POST /api/systems/reload` |
| KB search returns nothing fresh | `docker compose exec api python cli.py index` |
| SQLite slow / large | `docker compose exec api python cli.py maintain` |
| Schema migration error on startup | See `git log --oneline` for recent migrations (e.g. commit `5e05103` — SQLite schema migration); restart after pulling |
| Docker mount looks empty | Confirm you're editing files at `/opt/realizeos/engine/{shared,systems}` — those paths are bind-mounted into the container at the same names |

## File Reference

| File | Purpose |
| --- | --- |
| [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) | Engine architecture for AI coding agents (mirror each other) |
| [`realize-os.yaml`](realize-os.yaml) | Live config: ventures, features, LLM routing, channels, voice |
| [`docker-compose.yml`](docker-compose.yml) | `api` + `telegram` services |
| [`Dockerfile`](Dockerfile) | Python 3.12 base; runs `uvicorn realize_api.main:app` |
| [`.env.example`](.env.example) | Authoritative env-var contract |
| [`cli.py`](cli.py) | Engine CLI entry point |
| [`cli_agent_bot.py`](cli_agent_bot.py) | Standalone Telegram VPS-control bot |
| [`docs/configuration.md`](docs/configuration.md) | Config schema reference |
| [`docs/api-reference.md`](docs/api-reference.md) | REST API reference |
