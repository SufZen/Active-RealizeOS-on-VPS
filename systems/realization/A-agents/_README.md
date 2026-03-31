# Realization Agent Team — Overview & Routing Guide

## Team Roster

| # | Agent | File | Scope | Source Gems |
|---|-------|------|-------|-------------|
| 1 | **Orchestrator** | `orchestrator.md` | Routes requests, coordinates multi-agent work, session protocol | #10 Team Leader (simplified, no "ME") |
| 2 | **Strategist** | `strategist.md` | Ventures, brand, positioning, market intelligence | #11 Visionary Architect + #15 Strategic Venture Architect + #24 Global Market Intelligence + #25 Brand & Creative Director |
| 3 | **Writer** | `writer.md` | All content creation across channels | #8 Content Architect + #7 Sensual Brand Alchemist (voice layer) |
| 4 | **Reviewer** | `reviewer.md` | Quality review ALL outputs | Expanded from the-system |
| 5 | **Builder** | `builder.md` | RE projects, architecture, tech, automation, design | #26 Space & RE Steward + #6 Code Architect + #19 Digital Alchemist + #11 Visionary Architect (design layer) |
| 6 | **Operations** | `operations.md` | Finance, legal, compliance, contracts, HR, process | #18 Ops & Finance Guardian + #20 Juridical Compass + #22 HR & Talent Cultivator |
| 7 | **Community** | `community.md` | Client engagement, digital presence, community, SEO | #9 Digital Presence Dynamo + #23 Concierge AI |

## Quick Routing Guide

| "I need..." | → Agent(s) |
|-------------|-----------|
| A LinkedIn post / social content | Writer → Reviewer |
| To review content quality | Reviewer |
| Venture analysis / business strategy | Strategist + Operations |
| Property assessment / construction | Builder + Operations |
| A client proposal / contract | Operations → Reviewer |
| Brand positioning / creative direction | Strategist + Writer |
| SEO / digital marketing / community | Community |
| Investment ROI analysis | Builder + Strategist |
| System maintenance / agent updates | → shared-library meta-tools |
| Personal (non-business) | → shared-registry personal-system |

## Hierarchy

```
Human (Asaf)
    ↓
Orchestrator (routes, coordinates — no identity)
    ↓
┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│  Strategist  │    Writer    │   Builder    │  Operations  │  Community   │
│              │              │              │              │              │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
                                    ↓
                              Reviewer (reviews ALL outputs before delivery)
```

## Key Rules

1. **ALL outputs go through Reviewer** before delivery — no exceptions
2. **Orchestrator has no identity** — it routes, it doesn't create or opine
3. **Anti-patterns are hard constraints** — see `shared-registry/shared-core/anti-patterns.md`
4. **Memory updates happen after significant work** — learning-log, decisions, feedback
5. **Cross-entity work** uses `B-brain/portfolio/` context files and `shared-registry/entities/`

## Agent Independence Note

Agents for other entities are NOT part of this team. They operate in their own systems:

- **Burtucala** (ENT-02) → `Burtucala-System/` (BUILT — 5 agents: Orchestrator, Content Creator, Deal Analyst, Venture Builder, Reviewer)
- **Arena Habitat / MC** (ENT-04/05) → `MarvelousCreations-System/` (BUILT — 5 agents: Orchestrator, Project Director, Finance Controller, Capital & Sales, Architect)
- **HomeAid** (ENT-03) → `HomeAid-System/` (FUTURE — quoting skill extracted to entity-specific-skills for interim use)

All Burtucala work should be routed through Burtucala-System. All Arena Habitat/MC work should be routed through MarvelousCreations-System. Only public content about Arena Habitat flows through Realization's Writer.

---

## Shared Agents (from shared-library)

These agents serve ALL ventures. Load from `../shared-library/agents/`:

| Agent | Scope | When to Route |
|-------|-------|---------------|
| Design Director | Visual design, presentations, brand materials | Design requests, pitch decks, marketing visuals |
| Marketing & Growth | SEO, email funnels, analytics, conversion | Growth strategy, SEO, email sequences, analytics |

---

> Entity: ENT-01 Realization | System: systems/realization
