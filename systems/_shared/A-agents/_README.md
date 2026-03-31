# Shared Agents

Agents that serve **all ventures** in the Suf Zen ecosystem. These are not tied to a single entity — they load the requesting venture's brand context (`C-core/`) and operate within that venture's voice and standards.

## Why Shared?

Some capabilities are needed across all ventures but shouldn't be duplicated per system:
- **Design** — Realization, Burtucala, MC, and emerging platforms all need visual design
- **Marketing & Growth** — All ventures need SEO, email strategy, and analytics

Shared agents prevent fragmentation and ensure consistency.

## Agent Registry

| Agent | File | Scope |
|-------|------|-------|
| Design Director | `design-director.md` | Visual design, presentations, brand materials, web/digital design |
| Marketing & Growth | `marketing-growth.md` | SEO strategy, email funnels, social strategy, analytics, conversion optimization |

## How to Use

1. **Route via orchestrator:** Each system's orchestrator routes design/marketing requests here
2. **Load brand context:** The shared agent reads the requesting venture's `C-core/brand-identity.md` and `C-core/brand-voice.md`
3. **Gatekeeper review:** All outputs go through the requesting venture's Gatekeeper
4. **Skills loading:** Each agent lists which skills from `../skills/` to load per task type

## Loading Pattern

```
1. Load shared agent definition (this directory)
2. Load requesting venture's C-core/ (brand identity + voice)
3. Load relevant skills from skills library (per agent's Skills Library References table)
4. Execute task
5. Route output through venture's Gatekeeper
```
