# RealizeOS — State Map

Current state of the AI platform development. Update regularly for builder agent context.

**Last updated**: 2026-03-24

## Current Phase

**Phase:** v03 Full — Post-migration, engine optimization
**Editions:** Full (9-system, Docker) + Lite (single-system, template-driven)

## Current Priorities

1. Engine bug fixes — LLM routing, analytics wiring, evolution integration — Status: In progress (Sprint 1)
2. Dormant feature activation — cross-system intelligence, cost tracking — Status: In progress (Sprint 2)
3. Content & intelligence improvements — summarization, smarter routing — Status: Planned (Sprint 3)
4. Business automation — portfolio briefing, webhooks — Status: Planned (Sprint 4)

## Active Workstreams

### Sprint 1: Critical Fixes (Active)
- YAML LLM routing wired into router.py
- Analytics tracking wired into process_message()
- V1 skills and review routed through multi-LLM router
- Evolution handler integrated into pipeline

### Sprint 2: Activate Dormant Power (Active)
- Cross-system context enabled
- State maps created for all systems
- LLM cost tracking to be wired
- Gap analysis pipeline to be connected

### Sprint 3: Intelligence (Planned)
- Conversation summarization
- File cache mtime invalidation
- Smarter agent selection (LLM-assisted)
- API endpoints for analytics/evolution

### Sprint 4: Business Automation (Planned)
- Daily portfolio briefing skill
- Webhook-triggered automations
- Auto-prompt refinement

## Deferred Items

- Super Agent Telegram bot (deferred by Asaf)
- Voice Phase 3 (live calls)
- Docker image rebuild (using docker cp for now)

## Technical Debt

- Python source baked into Docker image (not volume-mounted)
- Config.py shared path handling
- Detector.py shared skills merge edge cases

## Key Dates

- 2026-03-24 — Sprint 1+2 execution
- [TBD] — Docker image rebuild
- [TBD] — Lite edition sync
