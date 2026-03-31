# Investment Agent v1 Project Context

## Tech Stack

```yaml
tech_stack:
  language: python 3.x
  framework: RealizeOS + FastAPI
  workflow_engine: YAML skills v1/v2
  storage: markdown KB + SQLite memory
  research_tools:
    - Brave web search
    - web fetch
  deployment: existing RealizeOS runtime
```

## Conventions

```yaml
conventions:
  naming: "snake_case for config keys and agent ids; kebab-case for markdown file names"
  planning: "BMAD docs live under docs/dev-process/plans"
  systems: "personal-investments and company-investments stay separate"
  skills: "prefer skill-first workflows over adding more permanent agents"
  outputs: "every proposal is structured, sourced, and approval-aware"
```

## Architecture Decisions

```yaml
architecture_decisions:
  - "Use two investment systems, not one combined desk."
  - "Keep a four-agent core team only: orchestrator, investment_cio, risk_controller, execution_controller."
  - "Use shared protocols/templates under systems/_shared for cross-system consistency."
  - "Default authority mode is paper mode with an explicit authority ladder."
  - "Private and manual assets remain manual-input first in v1."
```

## Implementation Rules

```yaml
implementation_rules:
  - "Risk controller can veto any recommendation that breaks policy or authority mode."
  - "No live trading path is enabled in v1."
  - "Do not create a bespoke CLI for investment operations in v1."
  - "Mixed-source reconciliation must happen before recommendations rely on position data."
  - "Cross-system dashboards may read both systems, but ordinary prompts must not implicitly merge them."
```

## Anti-Patterns

```yaml
anti_patterns:
  - "Do not add specialist agents when a skill can encode the workflow."
  - "Do not optimize solely on short-term market trends or same-day PnL."
  - "Do not present unsourced numbers as facts."
  - "Do not bypass authority mode or approval requirements in prompts."
  - "Do not let company and personal policy files drift without an explicit review."
```
