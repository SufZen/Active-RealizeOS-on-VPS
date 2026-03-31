# RealizeOS — Platform & Business Overview

## What RealizeOS Is

A self-hosted AI operations engine for entrepreneurs and small ventures. Built by Asaf Eyzenkot, RealizeOS enables any business to deploy a structured AI agent system — with multi-system support, skill routing, and multi-LLM backends — without being locked into any single AI provider.

**Tagline:** The AI infrastructure layer for real business operators.
**Status:** Active development — v03 (Full) in production, Lite edition for simpler deployments.
**Creator:** Asaf Eyzenkot (Realization)

---

## Product Architecture

```
realize-os/
├── realize_core/          Python engine (message processing, routing, LLM)
├── realize_api/           FastAPI REST API (port 8080)
├── systems/               User's knowledge bases (FABRIC structure)
│   ├── _shared/           Cross-system identity, protocols, shared agents
│   └── [venture]/         Per-venture FABRIC directories
└── templates/             8 business templates (consulting, agency, etc.)
```

### FABRIC Directory Structure (per system)
- **F-foundations** — Brand identity, values, anti-patterns
- **A-agents** — Agent persona files (.md)
- **B-brain** — Knowledge base (domain knowledge, market data)
- **R-routines** — Skills, workflows, SOPs
- **I-insights** — Memory, logs, analytics
- **C-creations** — Output files (reports, drafts, campaigns)

---

## Multi-LLM Strategy

RealizeOS supports multiple AI providers with intelligent routing:

| Task Type | Model |
|-----------|-------|
| Simple Q&A | Gemini Flash |
| Content creation | Claude Sonnet |
| Strategy & analysis | Claude Sonnet |
| Deep reasoning / finance | Claude Opus |
| Code generation | Claude Sonnet |
| Image generation | Gemini Pro Vision |
| Video tasks | Veo 2 |
| Data analysis | Claude Opus |

Providers: Anthropic (Claude), Google (Gemini/Veo), OpenAI, Ollama (local)
Auto-discovery: Available providers detected at startup based on API keys.

---

## Two Editions

### RealizeOS Full (v03)
- Multi-system (8 ventures in parallel)
- Full FABRIC structure
- Shared layer (_shared)
- Skills v1 + v2 (YAML-based)
- Docker deployment
- API + Telegram channels

### RealizeOS Lite
- Single-system
- Simplified FABRIC structure
- 4 core agents (orchestrator, writer, analyst, reviewer)
- Template-driven setup (8 business templates)
- Ideal for solo operators or single-venture businesses

---

## Business Model (Under Development)

**Who it's for:**
- Entrepreneurs running multiple ventures (Asaf's own use case)
- Agency operators needing AI systematization
- Consultants wanting AI-augmented delivery
- Small teams wanting structured AI without enterprise costs

**Potential monetization:**
- Hosted version (SaaS)
- Done-for-you migration and setup services
- Templates marketplace
- White-label licensing

---

## Current Development Priorities

1. Complete 8-system migration (this project)
2. Super Agent Telegram bot (post-migration)
3. Skills optimization per Anthropic guide
4. Advanced LLM routing (multi-model variety)
5. Scheduling and webhook integrations

---

## Key Technical Patterns

### Agent Auto-Discovery
Drop `.md` files in `A-agents/` → engine finds them via `config.py:_discover_agents()`

### Skills Auto-Loading
Drop `.yaml` files in `R-routines/skills/` → `skills/detector.py` loads them

### 12-Layer Prompt Assembly
`prompt/builder.py` assembles: identity → brand → agent → skills → memory → tools → instructions

### Message Flow
`Channel → base_handler.process_message() → session → skill check → agent routing → LLM`

---

## Competitive Positioning

**vs. ChatGPT plugins:** RealizeOS is self-hosted, multi-venture, and context-persistent
**vs. LangChain:** Higher-level abstraction, business-operator focused, no code required for users
**vs. Make.com AI:** Deeper agent personas, KB integration, not just workflow automation
**vs. Claude Projects:** Structured multi-system, custom routing, deployable as an API

---

## Key References

- Engine source: `G:\RealizeOS-Full-V03\realize_core\`
- Lite edition: `G:\RealizeOS-Lite-V03- Test\`
- Templates: `G:\RealizeOS-Full-V03\templates\`
- Architecture docs: `G:\RealizeOS-Full-V03\CLAUDE.md`
