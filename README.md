# Active RealizeOS — VPS Instance

This is the live RealizeOS deployment behind Asaf's business ecosystem. It runs **10 ventures + a `_shared` cross-system layer**, exposes a REST API, and drives two Telegram bots — all on a single VPS managed by systemd and Docker Compose. A separate standalone bot (`cli_agent_bot.py`) gives Telegram-only operator access to the box.

If you're looking for the public RealizeOS product (the shippable Lite vault and Full distribution), see `realize_lite/`, `docs/lite-guide.md`, and `docs/full-guide.md`. This README is for working **on** the active VPS, not packaging.

## Where to Look

| You want to... | Read |
| --- | --- |
| Understand the engine architecture and the live config | [`CLAUDE.md`](CLAUDE.md) (or [`AGENTS.md`](AGENTS.md) — same content) |
| Bring up / operate the VPS deployment | [`setup-guide.md`](setup-guide.md) |
| Look up env vars and config schema | [`docs/configuration.md`](docs/configuration.md), [`.env.example`](.env.example) |
| Hit the REST API | [`docs/api-reference.md`](docs/api-reference.md) |
| Author a new skill | [`docs/skill-authoring.md`](docs/skill-authoring.md) |
| Contribute code | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Find the live ventures | [`realize-os.yaml`](realize-os.yaml) and `systems/<key>/` |

## Live Ventures

Source of truth: [`realize-os.yaml`](realize-os.yaml).

| Key | Domain |
| --- | --- |
| `realization` | Portugal real-estate operations |
| `realization-il` | Venture architecture studio (Israel) |
| `burtucala` | Real estate & PropTech (Portugal) |
| `arena` | Real-estate development (Arena Habitat SPV) |
| `homeaid` | Remote management & expat services |
| `mioliving_partnership` | Italian real-estate partnership |
| `personal` | Personal & lifestyle intelligence |
| `personal-investments` | Personal portfolio operations |
| `company-investments` | Treasury allocation |
| `realizeos` | RealizeOS engine & platform |
| `_shared` | Cross-system identity, anti-patterns, shared agents |

Each venture lives under `systems/<key>/` and follows the **FABRIC** structure: `F-foundations/`, `A-agents/`, `B-brain/`, `R-routines/`, `I-insights/`, `C-creations/`. Cross-venture content (identity, methods, deal dossiers) lives under `shared/`.

## Architecture

```
        ┌────────────┐     ┌────────────┐     ┌────────────┐
        │ Sufz bot   │     │ Paulo bot  │     │ REST API   │   Channels
        │ (super)    │     │ (personal) │     │ port 8080  │
        └─────┬──────┘     └─────┬──────┘     └─────┬──────┘
              └───────────┬──────┴────────────┬─────┘
                          ▼                   ▼
                ┌────────────────────────────────┐
                │    realize_core.engine          │ Channel-facing entry
                │    base_handler.process_message │ Session → skill → agent
                └────────────────┬───────────────┘
                                 ▼
                ┌────────────────────────────────┐
                │       LLM Router               │ classifier → registry
                │  simple → Gemini Flash         │
                │  content/strategy → Sonnet 4.6 │
                │  complex/data → Opus 4.6       │
                │  code → Sonnet 4.6             │
                └────────────────┬───────────────┘
                                 ▼
                ┌────────────────────────────────┐
                │     Prompt Builder              │ 12-layer assembly from KB
                └────────────────┬───────────────┘
                                 ▼
                ┌────────────────────────────────┐
                │   Tools (Google / Web / Browser │
                │   / MCP / KB / Voice)           │
                └────────────────┬───────────────┘
                                 ▼
                ┌────────────────────────────────┐
                │ Evolution: gap-detect, suggest, │
                │ refine (auto-apply OFF)         │
                └────────────────────────────────┘
```

A separate process — **`cli_agent_bot.py`** — runs alongside the engine (also via systemd) to expose a small set of VPS-control commands (Claude Code CLI, Gemini CLI, git, system status) over Telegram for authorized operators. It does **not** go through the engine pipeline above.

## CLI

```bash
python cli.py serve                           # Start FastAPI on 127.0.0.1:8080
python cli.py bot --name sufz                 # Run a specific Telegram bot
python cli.py status                          # System status
python cli.py index                           # Rebuild KB search index
python cli.py evolve                          # Run gap analysis + skill/prompt suggestions
python cli.py maintain                        # SQLite VACUUM + ANALYZE
python cli.py venture create --key NEW        # Scaffold a new venture
python cli.py venture list
python cli.py init --template consulting      # (Used to scaffold the public Full distribution)
python cli.py init --setup setup.yaml         # One-shot init from a setup file
```

## REST API (operator quick reference)

Base URL: `http://localhost:8080` (or your VPS host). Auth via `Authorization: Bearer $REALIZE_API_KEY` or `X-API-Key`.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/chat` | Send a message, get an AI response |
| GET / DELETE | `/api/conversations/{system_key}/{user_id}` | History read/clear |
| GET | `/api/systems[/{key}[/agents\|/skills\|/sessions/{user}]]` | Inspect configured systems |
| POST | `/api/systems/reload` | Hot-reload `realize-os.yaml` |
| GET | `/api/analytics[/{key}]` | Usage analytics |
| GET / POST | `/api/evolution/...` | Suggestions, run, approve, dismiss, refine, changelog |
| POST | `/webhooks/trigger-skill` | Fire a skill from an external system |
| POST | `/webhooks/{endpoint_name}` | Generic webhook intake |
| GET | `/health`, `/status` | Health + detailed status |

Full schema: [`docs/api-reference.md`](docs/api-reference.md).

## Quick Test

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $REALIZE_API_KEY" \
  -d '{"message": "Status check across all ventures", "system_key": "realizeos", "user_id": "operator"}'
```

## License

Engine: MIT. Live KB content under `shared/` and `systems/` is private operational data — do not redistribute.
