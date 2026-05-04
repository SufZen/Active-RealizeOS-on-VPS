# Contributing to RealizeOS

Welcome! We're glad you're interested in contributing.

## Quick Start

```bash
git clone https://github.com/SufZen/realize-os.git
cd realize-os
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov ruff
pytest
```

## Development Setup

1. **Fork and clone** the repository.
2. **Create a virtual environment**: `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`).
3. **Install runtime + dev tooling**: `pip install -r requirements.txt && pip install pytest pytest-asyncio pytest-cov ruff`.
4. **Run tests**: `pytest` (CI enforces coverage ≥ 50% — see `pyproject.toml`).
5. **Lint**: `ruff check realize_core/ realize_api/ tests/` and `ruff format --check realize_core/ realize_api/ tests/`.

## How to Contribute

### Report Bugs

Open an issue with:
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS

### Add a New Tool

Follow the [Build Your First Tool](docs/dev-process/reference/build-your-first-tool.md) guide:

1. Create a class extending `BaseTool`
2. Define schemas with `ToolSchema`
3. Implement `execute()` and `is_available()`
4. Register with `ToolRegistry`
5. Add tests

### Add a New Channel

Follow the [Build Your Own Channel](docs/dev-process/reference/build-your-own-channel.md) guide:

1. Create a class extending `BaseChannel`
2. Implement `start()`, `stop()`, `send_message()`, `format_instructions()`
3. Add tests

### Add a Skill

1. Create a YAML skill file in `skills/`
2. Define system prompt, agent key, and tools
3. Test via the API channel

## Code Standards

- **Python 3.11+** with type hints
- **pytest** for all tests
- **Docstrings** on all public functions and classes
- **No unused imports** — CI will catch these
- Follow existing patterns observed in the codebase

## Project Structure

```
realize_core/
├── base_handler.py    # Single message-processing pipeline
├── engine.py          # Channel-facing runtime entrypoint
├── config.py          # YAML loader + auto-discovery
├── scaffold.py        # Venture create/delete/list
├── prompt/            # 12-layer prompt assembly
├── llm/               # Provider registry, router, classifier, providers/
├── memory/            # SQLite-backed conversation history
├── pipeline/          # Creative sessions
├── kb/                # FTS5 + vector KB index
├── skills/            # v1 + v2 skill detection and execution
├── tools/             # Tool SDK + implementations (Google, web, browser, MCP, KB, voice)
├── channels/          # api, telegram, scheduler, web, webhooks, whatsapp
├── workflows/         # Workflow engine
├── media/             # Media processing
├── security/          # RBAC, audit, vault
├── utils/             # Shared helpers
└── evolution/         # Gap detection, skill suggestion, prompt refinement

realize_api/routes/    # FastAPI routers: chat, systems, evolution, webhooks, health
```

The user-facing CLI is `cli.py` at the repo root. `cli_agent_bot.py` (also at the root) is a separate standalone Telegram bot for VPS control — not part of the engine pipeline.

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass (`pytest`)
4. Update docs if adding new features
5. Submit a PR with a clear description

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
