# Suf Zen Ecosystem Dashboard

> Single-pane overview of all systems, agents, methods, and integrations.

---

## Ecosystem Map

```
ENT-00 ASAF EYZENKOT (Founder)
    |
ENT-01 REALIZATION (Venture Studio — Parent)
    |
    +-- ENT-02 Burtucala (Venture-Building Studio)
    |   +-- System: Burtucala-System (5 agents)
    |   +-- Partners: Asaf + Noam Perets
    |
    +-- ENT-03 HomeAid (Property Services) — future system
    |
    +-- ENT-04 Arena Habitat (10-unit RE development)
    |   +-- ENT-05 Marvelous Creations LDA (SPV)
    |       +-- System: MarvelousCreations-System (5 agents)
    |       +-- GP: Asaf + Roy + Meirav | LP: Zodiaco (Eldad)
    |       +-- ENT-06 Boa Arc (Architectural brand)
    |
    +-- ENT-07 Second Base (Multi-local platform) — future system
    +-- ENT-08 Sexy.Barcelona (Content platform) — future system
```

---

## Active Systems

### ENT-01 Realization — 7 Agents

| Agent | Role | Key Methods |
|-------|------|-------------|
| Orchestrator | Routes requests, session protocol | MTH-40 |
| Strategist | Ventures, brand positioning, market intelligence | MTH-14, MTH-18 |
| Copywriter | Content across all channels | MTH-10, MTH-12, MTH-13, MTH-30 |
| Gatekeeper | Quality review (mandatory gate) | MTH-42 |
| Builder | RE projects, architecture, construction | MTH-15, MTH-16, MTH-17 |
| Operations | Finance, legal, contracts, compliance | MTH-19, MTH-20 |
| Community & Digital | Client engagement, SEO, marketing | MTH-13, MTH-18, MTH-20 |

**Active methods:** MTH-10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 30, 31, 40, 42, 43
**Voice:** Two registers — Hebrew warm/community, English structured/professional
**Telegram:** @Realizationbotbot

### ENT-02 Burtucala — 5 Agents

| Agent | Role | Key Methods |
|-------|------|-------------|
| Orchestrator | Routes requests | — |
| Content Creator | Blog, LinkedIn, newsletter (4 pillars x 6 formats) | MTH-12, MTH-13, MTH-30 |
| Deal Analyst | Syndicate DD, investment analysis, Golden Rating | MTH-15, MTH-17 |
| Venture Builder | Sprint management (0-3), space programs, SOPs | MTH-14, MTH-17 |
| Gatekeeper | Accuracy, no em dashes, numbers-first | MTH-42 |

**Active methods:** MTH-12, 13, 14, 15, 17, 30, 42
**Voice:** English only. Operator voice. Numbers before adjectives. No em dashes.
**Telegram:** @Burtucala_bot

### ENT-05 Marvelous Creations — 5 Agents

| Agent | Role | Key Methods |
|-------|------|-------------|
| Orchestrator | Routes requests | — |
| Project Director (Asaf) | Technical strategy, licensing, contractors, timeline | MTH-15, MTH-16 |
| Finance Controller (Roy) | Budget, treasury, payments, reporting | MTH-47, MTH-48, MTH-42 |
| Capital & Sales (Meirav) | Investor relations, sales pipeline, CPCVs | MTH-47, MTH-46 |
| Architect (BOA Arc) | Design vision, PIP/licensing docs, SFRG coordination | MTH-16 |

**Active methods:** MTH-15, 16, 17, 19, 42, 46, 47, 48
**Voice:** Professional, transparent, precise. Governance-aware.
**Governance:** Internal GP <5K | Joint GP 5-10K | LP approval >10K | Variance >2.5% flagged
**Telegram:** @MCArenaHabitat_bot

---

## Cross-Venture Router

**@SufZenBot** — Routes messages to the correct system using 3-tier classification:

1. Command routing (`/content` > Realization, `/deal` > Burtucala, `/budget` > MC)
2. Keyword scoring (confidence threshold 60%)
3. LLM fallback (Gemini Flash classification)

---

## Shared Library Status

| Category | Active | Planned | Total |
|----------|--------|---------|-------|
| Skills (MTH-10 to 29) | 4 | 8 | 12 |
| Workflows (MTH-30 to 39) | 1 | 4 | 5 |
| Protocols (MTH-40 to 49) | 4 | 5 | 9 |
| Agent Templates (MTH-01 to 09) | 0 | 3 | 3 |
| Meta-Tools (MTH-50 to 59) | 0 | 4 | 4 |
| Prompts (MTH-60 to 69) | 0 | 5 | 5 |
| **Total** | **9** | **29** | **38** |

### Active Methods (files exist with full content)

| MTH | Name | Used By |
|-----|------|---------|
| MTH-12 | Content Creation Skill | Realization, Burtucala |
| MTH-13 | Content Repurpose Skill | Realization, Burtucala |
| MTH-15 | Deal Evaluation Skill | Realization, Burtucala, MC |
| MTH-17 | ROI Modeling Skill | Realization, Burtucala, MC |
| MTH-30 | Content Workflow | Realization, Burtucala |
| MTH-42 | Quality Review Protocol | ALL systems |
| MTH-46 | Cross-Entity Protocol | Burtucala, MC |
| MTH-47 | Investor Reporting Protocol | MC |
| MTH-48 | Payment Cycle Protocol | MC |

---

## Person Registry

| ID | Name | Role | Active In |
|----|------|------|-----------|
| PER-00 | Asaf Eyzenkot | Founder, owner of all entities | All systems |
| PER-01 | Meirav Gonen | Partner (personal + MC Capital & Sales) | MC |
| PER-02 | Noam Perets | Burtucala co-founder | Burtucala |
| PER-03 | Roy Hadar | MC Finance Controller (GP) | MC |
| PER-04 | Eldad Stinbook | MC LP investor (Zodiaco) | MC |

---

## Infrastructure

### Telegram Bots

| Bot | System | Status | Token Config |
|-----|--------|--------|-------------|
| @SufZen_bot | Cross-venture router | Running | .env: SUFZEN_BOT_TOKEN |
| @Realizationbotbot | ENT-01 Realization | Running | .env: REALIZATION_BOT_TOKEN |
| @Burtucala_bot | ENT-02 Burtucala | Running | .env: BURTUCALA_BOT_TOKEN |
| @MCArenaHabitat_bot | ENT-05 MC | Running | .env: MC_BOT_TOKEN |

**Hosting:** Local (long polling) — Cloud Run deployment pending
**Authorized users:** Asaf (5864595882) — partners to be added later

### LLM Configuration

| Provider | Model | Used For | Cost |
|----------|-------|----------|------|
| Google Gemini | 2.5 Flash | Routing, simple Q&A, content drafts | ~Free |
| Anthropic Claude | Sonnet | Reasoning, financial analysis, reviews | $3/$15 per 1M tokens |
| Anthropic Claude | Opus | Complex strategy, cross-venture | $15/$75 per 1M tokens |

### MCP Servers (Claude Desktop)

| Server | Status | Notes |
|--------|--------|-------|
| filesystem | Active | Full workspace access |
| google-drive | Planned | OAuth needed (3 accounts) |
| gmail-realization | Planned | info@realization.co.il |
| gmail-burtucala | Planned | asaf@burtucala.com |
| gmail-personal | Planned | asafazenkot@gmail.com |
| brave-search | Planned | Free API key needed |
| clickup | Planned | API token needed |
| google-calendar | Planned | OAuth (multi-account) |
| make-webhooks | Planned | Existing Make.com account |

### Version Control

| Repo | Platform | Status |
|------|----------|--------|
| asaf-kb-workspace | GitHub (private) | Active — SufZen/asaf-kb-workspace |
| suf-zen-telegram | Local | Pending GitHub repo creation |

**Obsidian Git:** Auto-sync configured (10 min interval)

---

## Monthly Cost Estimate

| Item | Cost |
|------|------|
| GitHub | Free |
| Telegram bots | Free |
| Hosting (Cloud Run) | Free |
| Gemini API | Free / ~$1-5 |
| Claude API | ~$5-30 |
| **Total** | **~$5-35/month** |

---

> Last updated: 2026-02-10
> Next review: Update after Phase 4 (MCP connections) and Cloud Run deployment
