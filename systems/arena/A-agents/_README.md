# Arena Agent Team — Routing Guide

> Entity: ENT-05 | 5 agents | Arena Habitat SPV (3-pillar GP structure)

---

## Team Overview

```
                    +---------------+
                    | ORCHESTRATOR  |
                    | (no identity) |
                    +-------+-------+
          +----------+-----+-----+-----------+
          v          v           v            v
   +-----------+ +-----------+ +---------+ +----------+
   |  PROJECT  | |  FINANCE  | | CAPITAL | | ARCHITECT|
   |  DIRECTOR | | CONTROLLER| | & SALES | |          |
   +-----------+ +-----------+ +---------+ +----------+
     Asaf's       Roy's         Meirav's     BOA Arc
     Pillar       Pillar        Pillar       (under Arena)
```

## Agent Roster

| # | Agent | File | Scope |
|---|-------|------|-------|
| 1 | **Orchestrator** | `orchestrator.md` | Routes requests. No identity. |
| 2 | **Project Director** | `project-director.md` | Asaf's pillar: technical strategy, licensing/PIP, banking, contractor tendering, marketing, timeline. |
| 3 | **Finance Controller** | `finance-controller.md` | Roy's pillar: budget gatekeeper, treasury, payment cycle, accounting (Audax), VAT, monthly reporting, variance monitoring. |
| 4 | **Capital & Sales** | `capital-sales.md` | Meirav's pillar: investor relations (LP/Eldad), sales execution, real estate agencies, CPCVs, capital waterfall, capital calls. |
| 5 | **Architect** | `architect.md` | BOA Arc role (while under Arena): design vision, PIP/licensing docs, engineering coordination with SFRG. |

## Routing Rules

| Request Type | Route To | Why |
|-------------|----------|-----|
| "What's the licensing status?" | Project Director | Licensing = Asaf's pillar |
| "Process this invoice..." | Finance Controller | Payments = Roy's pillar |
| "Prepare the monthly LP report..." | Finance Controller | Reporting = Roy's pillar |
| "Update Eldad on the sales pipeline..." | Capital & Sales | LP relations = Meirav's pillar |
| "Draft a CPCV for unit 3..." | Capital & Sales | Sales contracts = Meirav's pillar |
| "Review the architectural plans..." | Architect | Design = BOA Arc |
| "Submit the PIP documents..." | Project Director + Architect | Technical + design |
| "What's the budget status?" | Finance Controller | Budget = Roy's pillar |
| "Tender for general contractor..." | Project Director | Contractor tendering = Asaf's pillar |
| "Schedule the NovoBanco meeting..." | Project Director | Banking = Asaf's pillar |

## Governance-Aware Routing

All financial decisions route through the Joint Decision Axis:

| Decision Size | Route |
|--------------|-------|
| < 5,000 | Finance Controller (internal GP approval) |
| 5,000 - 10,000 | Finance Controller + Project Director (joint GP) |
| > 10,000 | Finance Controller + Project Director + flag for LP approval |
| > 2.5% variance | Finance Controller prepares LP notification |

## Multi-Agent Coordination

### Invoice Processing Flow
1. **Project Director** validates technical completion
2. **Architect** confirms design compliance (if construction-related)
3. Fiscalizacao signs off (external)
4. **Finance Controller** checks budget line + processes payment

### Monthly Reporting Flow
1. **Finance Controller** closes month financials
2. **Project Director** provides technical progress update
3. **Capital & Sales** provides sales pipeline update
4. **Finance Controller** compiles Monthly Management Report
5. Report sent to LP + Zoom review scheduled

### Sales Flow
1. **Capital & Sales** manages buyer relationship
2. **Project Director** confirms unit availability and specifications
3. **Finance Controller** validates financial terms
4. **Capital & Sales** executes CPCV (with legal review via Tania)

## Cross-Entity Notes

- **NO public content creation.** Arena does not produce blog posts, LinkedIn, or newsletters. Content about Arena Habitat goes through Realization's Writer.
- **Financial reporting** to LP is Arena-internal. Realization sees it as portfolio oversight.
- **Shared resources:** All agents access `../shared-registry/` and `../shared-library/` for entity IDs and method definitions.

---

## Shared Agents (from shared-library)

These agents serve ALL ventures. Load from `../shared-library/agents/`:

| Agent | Scope | When to Route |
|-------|-------|---------------|
| Design Director | Visual design, presentations, brand materials | Design requests, pitch decks, marketing visuals |
| Marketing & Growth | SEO, email funnels, analytics, conversion | Growth strategy, SEO, email sequences, analytics |
