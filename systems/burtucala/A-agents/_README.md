# Burtucala Agent Team — Routing Guide

> Entity: ENT-02 | 5 agents | Venture-building & RE consulting

---

## Team Overview

```
                    ┌─────────────┐
                    │ ORCHESTRATOR│
                    │  (no identity)│
                    └──────┬──────┘
            ┌──────────┼──────────┬────────────┐
            ▼          ▼          ▼            ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
     │  WRITER  │ │   DEAL   │ │ VENTURE  │ │ REVIEWER │
     │          │ │ ANALYST  │ │ BUILDER  │ │          │
     └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

## Agent Roster

| # | Agent | File | Scope |
|---|-------|------|-------|
| 1 | **Orchestrator** | `orchestrator.md` | Routes requests. No brand identity. |
| 2 | **Writer** | `writer.md` | Blog, LinkedIn, newsletters. 4 pillars x 6 formats. Burtucala operator voice. GEO-optimized. |
| 3 | **Deal Analyst** | `deal-analyst.md` | Deal underwriting, Syndicate dossiers, investment analysis, licensing pathways. |
| 4 | **Venture Builder** | `venture-builder.md` | Sprint management (0-3), venture architecture, space programs, ops design, SOPs. |
| 5 | **Reviewer** | `reviewer.md` | Quality review: accuracy, no em dashes, numbers-first, no invented details, GEO compliance. |

## Routing Rules

| Request Type | Route To | Why |
|-------------|----------|-----|
| "Write a blog post about..." | Writer | Content creation = Writer |
| "Analyze this deal / property..." | Deal Analyst | Investment analysis = Deal Analyst |
| "Create a space program for..." | Venture Builder | Venture architecture = Venture Builder |
| "Review this article for..." | Reviewer | Quality review = Reviewer |
| "What service should we recommend?" | Orchestrator | Orchestrator decides routing |
| "Draft a sprint plan for..." | Venture Builder | Sprint methodology = Venture Builder |
| "Write a Syndicate dossier..." | Deal Analyst + Writer | DD output = Deal Analyst, narrative = Writer |
| "Check if this content is ready..." | Reviewer | Final check = Reviewer |

## Quality Loop

```
Writer / Deal Analyst / Venture Builder
    → creates output
    → sends to Reviewer
    → Reviewer reviews (voice, accuracy, structure, GEO, CTA stage)
    → Approved? → Publish + log in I-insights/
    → Rejected? → Back to creator with specific feedback
```

## Cross-Entity Notes

- **NO Realization voice.** Burtucala has its own operator voice.
- **Content about Burtucala** is created here, NOT by Realization's Writer.
- **Content about Arena Habitat projects** is created by Realization's Writer, not here.
- **Shared resources:** All agents access `../_shared/` for shared foundations, protocols, and skills.

---

## Shared Agents (from _shared)

These agents serve ALL ventures. Load from `../_shared/A-agents/`:

| Agent | Scope | When to Route |
|-------|-------|---------------|
| Design Director | Visual design, presentations, brand materials | Design requests, pitch decks, marketing visuals |
| Marketing & Growth | SEO, GEO, email funnels, analytics, conversion | Growth strategy, SEO, email sequences, analytics |
