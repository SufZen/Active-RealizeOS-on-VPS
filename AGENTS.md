# AGENTS.md — RealizeOS Full Package (Development)

This is the RealizeOS Full package — a self-hosted AI operations engine. This file guides Codex when working on the engine codebase itself (not end-user AI behavior, which is handled by the KB's internal AGENTS.md).

## Architecture Overview

```
realize-os/
├── cli.py                    CLI entry point (init, serve, bot, status, venture)
├── realize-os.yaml           User's system configuration
├── realize_core/             Python engine
│   ├── base_handler.py       Message processing pipeline
│   ├── config.py             Config loader (YAML → dicts, feature flags)
│   ├── scaffold.py           Venture scaffolding (create/delete)
│   ├── prompt/
│   │   └── builder.py        Multi-layer prompt assembly (12 layers)
│   ├── llm/
│   │   ├── router.py         Task classification → model selection
│   │   ├── registry.py       Provider registry (auto-discovers available LLMs)
│   │   ├── base_provider.py  Abstract provider interface
│   │   ├── providers/        Codex, Gemini, OpenAI, Ollama adapters
│   │   ├── claude_client.py  Codex API client (direct, legacy)
│   │   └── gemini_client.py  Gemini API client (direct, legacy)
│   ├── memory/               Conversation history management
│   ├── pipeline/             Creative sessions (briefing → drafting → review)
│   ├── skills/               Skill detection and execution (v1 + v2)
│   ├── kb/                   Knowledge base indexing and search
│   ├── tools/                External tools (Google, web, browser, MCP)
│   ├── channels/             Channel adapters (API, Telegram)
│   └── evolution/            Self-improvement (gap detection, skill suggestion)
├── realize_api/              FastAPI REST API
├── realize_lite/             Embedded Lite package (used as scaffold source for cli.py init)
├── templates/                8 business templates (consulting, agency, portfolio, etc.)
├── tests/                    Test suite
└── docs/                     Documentation
```

## Key Patterns

### Message Flow
`Channel → base_handler.process_message() → session check → skill check → agent routing → LLM`

### Auto-Discovery
- **Agents**: Drop `.md` files in `A-agents/` → `config.py:_discover_agents()` finds them
- **Skills**: Drop `.yaml` files in `R-routines/skills/` → `skills/detector.py` loads them
- **Ventures**: `cli.py venture create` scaffolds FABRIC dirs → immediately available

### Feature Flags
Defined in `realize-os.yaml` under `features:`, accessed via `config.py:get_features()`:
- `review_pipeline` — auto-route to reviewer agent
- `auto_memory` — log learnings after interactions
- `proactive_mode` — include proactive layer in prompts
- `cross_system` — share context across all ventures

### Multi-LLM Routing
`router.py:classify_task()` → simple/content/complex → model selection via `ProviderRegistry`

The engine supports multiple LLM providers (Codex, Gemini, OpenAI, Ollama). Providers are auto-discovered at startup based on installed SDKs and configured API keys. The router uses the registry for provider-agnostic routing with automatic fallback chain (Codex → Gemini → OpenAI → Ollama).

## CLI Commands

```bash
python cli.py init --template NAME           # Initialize from template
python cli.py serve [--port PORT] [--reload] # Start API server
python cli.py bot                            # Start Telegram bot
python cli.py status                         # Show system status
python cli.py index                          # Rebuild KB search index
python cli.py venture create --key KEY       # Create new venture
python cli.py venture delete --key KEY       # Delete venture
python cli.py venture list                   # List ventures
```

## realize_lite/ as Scaffold Source

The `realize_lite/` directory is an embedded copy of the Lite package. It serves as the template source for `cli.py init` — its files are copied to the user's target directory. Changes to the Lite package must be synced here.

## Extending the System

### Adding a new tool
1. Create module in `realize_core/tools/`
2. Register in the tool dispatcher
3. Add task classification keywords in `llm/router.py`

### Adding a new channel
1. Create adapter in `realize_core/channels/` following `base.py` pattern
2. Add channel config support in `config.py`
3. Add CLI command if needed

### Adding a new LLM provider
1. Create provider in `realize_core/llm/providers/` extending `BaseLLMProvider`
2. Implement `name`, `complete()`, `list_models()`, `is_available()`
3. Register in `registry.py:auto_register()`

### Adding a new template
1. Create `.yaml` in `templates/` following existing format
2. Set `directory: systems/my-business-1` to match scaffold structure
3. Define `routing` and `agent_routing` sections
