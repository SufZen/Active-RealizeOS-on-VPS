# AGENTS.md — Active RealizeOS VPS Instance

> This file mirrors `CLAUDE.md` — keep them in sync. Both exist so any AI coding harness (Codex/Cursor read `AGENTS.md`, Claude Code reads `CLAUDE.md`) gets the same picture.

This repository is **the active RealizeOS VPS instance**, not a clean template or shippable distribution. It runs the live deployment behind Asaf Eyzenkot's business ecosystem — 10 ventures plus a `_shared` cross-system layer, two Telegram bots, a REST API, and a separate VPS-control bot. Treat the contents of `realize-os.yaml`, `systems/`, and `shared/` as production data.

For the public RealizeOS product (Lite vault + Full distribution) see `realize_lite/` and `docs/lite-guide.md`, `docs/full-guide.md`. Those describe the shippable form, not this repo.

## Where the Engine Runs

| Layer | What | Where |
| --- | --- | --- |
| Process manager | systemd | `/opt/realizeos/` on the VPS |
| API + Telegram services | Docker Compose | `docker-compose.yml` (services: `api`, `telegram`) |
| VPS-control bot | Standalone Python process | `cli_agent_bot.py` (separate from the engine) |
| Persistent state | SQLite | `./data/` (mounted into containers) |
| Knowledge base | Markdown files | `shared/`, `systems/<venture>/` |

`cli_agent_bot.py` is independent of `cli.py` — it gives a Telegram-only operator a way to drive Claude Code, Gemini CLI, and limited git/system commands on the VPS. Authorized users come from `AUTHORIZED_USERS`. See `cli_agent_bot.py:1–40`.

## Repository Layout

```
.
├── cli.py                       Engine CLI (init, serve, bot, status, index, evolve, maintain, venture)
├── cli_agent_bot.py             Standalone Telegram bot for VPS control (systemd)
├── realize-os.yaml              Live config: 10 ventures, features, LLM routing, channels, voice
├── docker-compose.yml           api + telegram services
├── Dockerfile                   Python 3.12 base, runs uvicorn realize_api.main:app
├── .env.example                 Full env var contract
├── setup.yaml.example           Optional one-shot init payload (cli.py init --setup)
├── requirements.txt
├── pyproject.toml               ruff config, pytest config (asyncio auto, coverage ≥50)
├── create_release_zip.py        Packages a public Lite/Full release zip
├── fix_lint.py                  Lint helper
├── realize_core/                Engine (see below)
├── realize_api/                 FastAPI app
├── realize_lite/                Embedded copy of the public Lite vault — used as scaffold by `cli.py init`
├── templates/                   8 business templates for `cli.py init --template`
├── shared/                      Cross-system identity, methods, deal dossiers, life events
├── systems/                     The 10 live ventures + _shared
├── scripts/                     One-off operational scripts
├── tests/                       pytest suite (see pyproject.toml fail_under = 50)
├── docs/                        Mixed: public-product docs + internal planning (banner-tagged)
└── realization-dashboard.html   Standalone HTML strategic dashboard (operator artifact)
```

### `realize_core/` (the engine)

```
realize_core/
├── base_handler.py     Single message-processing pipeline used by every channel
├── engine.py           Channel-facing runtime entrypoint; wraps base_handler.process_message
├── cli.py              Internal CLI helpers (root cli.py is the user-facing one)
├── config.py           YAML → dicts, feature flags, agent/venture discovery
├── scaffold.py         venture create/delete/list
├── prompt/             Multi-layer prompt assembly (12 layers)
├── llm/                Provider registry + router + capability table
│   ├── base_provider.py
│   ├── classifier.py            Keyword → task class
│   ├── router.py                Task class → model
│   ├── routing_engine.py        Higher-level routing decisions
│   ├── registry.py              Auto-discovers available providers
│   ├── claude_client.py         (Legacy direct client)
│   ├── gemini_client.py         (Legacy direct client)
│   ├── provider_capabilities.yaml
│   └── providers/{claude,gemini,openai,ollama}_provider.py
├── memory/             Conversation history (SQLite-backed)
├── pipeline/           Creative sessions (briefing → drafting → review)
├── skills/             v1 + v2 skill detection and execution; dev_workflows/
├── kb/                 KB indexing and search (FTS5 + vectors)
├── tools/              External tools — Google Workspace, web, browser, MCP, KB, voice
├── channels/           api, telegram, scheduler, web, webhooks, whatsapp
├── workflows/          Workflow engine
├── media/              Media processing
├── security/           RBAC, audit, vault
├── utils/              Shared helpers
└── evolution/          Gap detection, skill suggestion, prompt refinement
```

### `realize_api/`

```
realize_api/
├── main.py
├── middleware.py
└── routes/{chat,systems,evolution,webhooks,health}.py
```

## CLI Commands

```bash
python cli.py init --template NAME           # Initialize from template
python cli.py init --setup setup.yaml        # One-shot init from a setup file
python cli.py serve [--host H] [--port P]    # Start FastAPI (default 127.0.0.1:8080)
python cli.py serve --reload                 # Auto-reload during development
python cli.py bot [--name NAME]              # Start Telegram bot(s); --name picks one (sufz/paulo)
python cli.py status                         # Show system status
python cli.py index                          # Rebuild KB search index
python cli.py evolve                         # Run gap analysis and suggest improvements
python cli.py maintain                       # SQLite VACUUM + ANALYZE
python cli.py venture create --key KEY       # Create new venture (FABRIC scaffold + yaml entry)
python cli.py venture delete --key KEY --confirm KEY
python cli.py venture list                   # List ventures with status
```

`cli_agent_bot.py` is launched separately (systemd) — not via `cli.py`.

## The 10 Live Ventures + `_shared`

Source of truth: `realize-os.yaml`. One-line summary per system:

| Key | Directory | Domain |
| --- | --- | --- |
| `realization` | `systems/realization` | Portugal real-estate operations |
| `realization-il` | `systems/realization.co.il` | Venture architecture studio (Israel) |
| `burtucala` | `systems/burtucala` | Real estate & PropTech (Portugal) |
| `arena` | `systems/arena` | Real-estate development (Arena Habitat SPV) |
| `homeaid` | `systems/homeaid` | Remote management & expat services |
| `mioliving_partnership` | `systems/mioliving_partnership` | Italian real-estate partnership |
| `personal` | `systems/personal` | Personal & lifestyle intelligence |
| `personal-investments` | `systems/personal-investments` | Personal portfolio operations |
| `company-investments` | `systems/company-investments` | Treasury allocation |
| `realizeos` | `systems/realizeos` | RealizeOS engine & platform |
| `_shared` | `systems/_shared` | Cross-system identity, anti-patterns, shared agents |

Each venture follows the **FABRIC** structure: `F-foundations/`, `A-agents/`, `B-brain/`, `R-routines/`, `I-insights/`, `C-creations/`. Cross-system content lives in `shared/` (identity, user preferences, methods, deal dossiers).

## Key Patterns

### Message Flow
`Channel → engine.handle_message → base_handler.process_message → session check → skill check → agent routing → LLM`

### Auto-Discovery
- **Agents**: drop `.md` files in a venture's `A-agents/` → `config.py:_discover_agents()` finds them.
- **Skills**: drop `.yaml` files in `R-routines/skills/` → `skills/detector.py` loads them.
- **Ventures**: `cli.py venture create` scaffolds FABRIC dirs and adds the system entry to `realize-os.yaml`.

### Feature Flags (live values in `realize-os.yaml`)
| Flag | Live value | Effect |
| --- | --- | --- |
| `review_pipeline` | `true` | Auto-route publishable content through the Reviewer agent |
| `auto_memory` | `true` | Log learnings to the active system's `I-insights/learning-log.md` |
| `skills_v2` | `true` | Enable multi-step skill executor (agent/tool/condition/human) |
| `proactive_mode` | `false` | Suppress proactive-suggestion prompt layer |
| `cross_system` | `true` | Share state-map/venture summaries across systems |
| `evolution_engine` | `true` | Master switch for the self-evolution subsystem |
| `evolution_gap_detection` | `true` | Find unhandled patterns / repeated ad-hoc requests |
| `evolution_auto_apply` | `false` | Safety: evolution suggestions require explicit approval |
| `evolution_prompt_refine` | `true` | Suggest agent-prompt improvements from feedback |
| `evolution_skill_suggest` | `true` | Auto-generate skill YAML for detected gaps |

### Multi-LLM Routing
`llm.routing` in `realize-os.yaml` maps task classes to models. Live mapping:

| Class | Model | Used for |
| --- | --- | --- |
| `simple` | `gemini-flash` | Q&A, lookups, short replies |
| `content` | `claude-sonnet-4-6` | Writing, drafting, editing |
| `strategy` | `claude-sonnet-4-6` | Strategy and reasoning |
| `complex` | `claude-opus-4-6` | Deep analysis, financial modeling |
| `code` | `claude-sonnet-4-6` | Code generation, technical tasks |
| `image` | `gemini-pro-vision` | Image tasks |
| `video` | `veo-2` | Video understanding/generation |
| `data` | `claude-opus-4-6` | Structured analysis |

Per-system overrides live under `llm.system_overrides` (e.g., `arena.complex` pinned to Opus). Available providers are auto-discovered at startup based on installed SDKs and env keys (`ANTHROPIC_API_KEY`, `GOOGLE_AI_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_BASE_URL`). Fallback chain: Claude → Gemini → OpenAI → Ollama.

### Channels
| Type | Purpose | Notes |
| --- | --- | --- |
| `api` | REST API on port 8080 | `realize_api.main:app` |
| `telegram` (sufz) | Super-agent across all 10 systems | `mode: super_agent`, `topic_routing` maps forum thread IDs → system_key |
| `telegram` (paulo) | Pinned to `personal` | Portuguese bureaucracy concierge |
| `voice` | ElevenLabs + Twilio outbound | Webhooks under `/webhooks/elevenlabs` |
| `web`, `webhooks`, `whatsapp`, `scheduler` | In-tree adapters | Wire up via `realize-os.yaml → channels` as needed |

## Extending the System

### Adding a new tool
1. Create module in `realize_core/tools/` extending `BaseTool` (`tools/base_tool.py`).
2. Register with `ToolRegistry` (`tools/tool_registry.py`).
3. Add task-classification keywords in `realize_core/llm/router.py` (or `classifier.py`).
4. Add tests under `tests/test_tool_*.py`.

### Adding a new channel
1. Create adapter in `realize_core/channels/` following `base.py`.
2. Add a `channels:` entry in `realize-os.yaml`.
3. Wire startup in `cli.py` if it needs its own command.
4. Add tests under `tests/test_channel*.py`.

### Adding a new LLM provider
1. Create a class in `realize_core/llm/providers/` extending `BaseLLMProvider`.
2. Implement `name`, `complete()`, `list_models()`, `is_available()`.
3. Register in `registry.py:auto_register()`.
4. Add tests under `tests/test_registry.py` / `tests/test_base_provider.py`.

### Adding a new venture
Use `python cli.py venture create --key new-venture --name "New Venture"`. The scaffolder copies the FABRIC structure and appends a system entry to `realize-os.yaml`. Then fill `F-foundations/venture-identity.md` and `F-foundations/venture-voice.md` before relying on it.

### Adding a new template
1. Create `<name>.yaml` in `templates/` following the existing format.
2. Set `directory: systems/my-business-1` to match the scaffold layout.
3. Define `routing` and `agent_routing`.

## Testing & Quality

- `pytest` from the repo root. CI runs lint (`ruff check` + `ruff format --check`) then tests with coverage ≥ 50% (`pyproject.toml`).
- Test layout mirrors the engine modules — see `tests/`.
- Lint locally: `ruff check realize_core/ realize_api/ tests/`.

## Operating Notes

- **Config is live data.** Edits to `realize-os.yaml` and any file under `systems/` or `shared/` change behavior immediately on the next message — there is no separate "deploy" step for KB content because Docker mounts these directories at runtime (`docker-compose.yml`).
- **Three Telegram bots in `.env.example`**: `SUFZ_BOT_TOKEN` (super-agent), `PAULO_BOT_TOKEN` (Portugal), `CLI_AGENT_BOT_TOKEN` (`cli_agent_bot.py`). `AUTHORIZED_USERS` gates all of them.
- **Evolution suggestions never auto-apply.** `evolution_auto_apply: false` is intentional. Use `python cli.py evolve` to generate suggestions, then approve via the API (`/api/evolution/approve/{id}`).
- **`realize_lite/` is the scaffold source for `cli.py init`.** Treat it as the embedded copy of the public Lite vault. Don't import from it at runtime.
