> **Internal/historical document — not user-facing operator documentation. See root `CLAUDE.md` and `setup-guide.md` for current operating guidance.**

# PRD: Investment Agent v1

## Overview

Investment Agent v1 gives Asaf a controlled internal investment operator inside RealizeOS. It supports personal investing and company treasury/investment management as separate systems, produces daily briefs and proposal queues, and maintains policy-aware recommendations without enabling live autonomous trading in v1.

## User Stories

- As an operator, I want separate personal and company investment workspaces so that policy, memory, and audit trails stay clean.
- As an operator, I want a daily market and portfolio brief so that I can review changes quickly.
- As an operator, I want rebalance and paper-trade proposals with explicit rationale so that I can approve or reject them confidently.
- As a risk owner, I want an independent risk gate so that attractive ideas cannot bypass concentration, authority, or policy limits.
- As an operator, I want a cross-system dashboard so that I can compare personal and company posture without collapsing them into one system.

## Functional Requirements

### Feature 1: Dual Investment Systems
- Add `personal-investments` and `company-investments` as first-class systems in `realize-os.yaml`.
- Each system must auto-discover its own agents and skills.
- Each system must maintain independent state, policy, insights, and outputs.

### Feature 2: Policy And Guardrails
- Each system must include an investment policy, authority matrix, and risk rules document.
- The authority ladder must support `observe`, `recommend`, `paper_execute`, `live_with_approval`, and `autonomous_capped`.
- All recommendations must cite the active authority mode and whether approval is required.

### Feature 3: Skill-First Operations
- Add workflows for policy creation, holdings sync, daily brief, rebalance proposal, exception alert, and monthly review.
- Add one shared workflow for cross-system investment dashboards.
- Skills should use explicit context files rather than relying on broad cross-system prompt sharing.

### Feature 4: Audit-Friendly Outputs
- Rebalance and paper-trade proposals must include policy rule, source data, confidence, invalidation conditions, and approval requirement.
- Execution-controller outputs must be formatted for an approval queue or committee packet.
- The systems must include dedicated insight logs for theses, decisions, and performance reviews.

## Non-Functional Requirements

### Performance
- Daily brief workflows should complete with lightweight web research and KB context only.

### Security
- No live trading or secret brokerage actions in v1.
- Internal-use-only framing must be explicit in system prompts and policy docs.

### Scalability
- Skill and document structure must leave room for later broker/data adapters without changing the agent model.

### Reliability
- Missing policy or stale source data should degrade to warning/block behavior, not fabricated guidance.

## Information Architecture

- Two system directories under `systems/`
- Shared templates and protocols under `systems/_shared/R-routines/`
- BMAD planning artifacts under `docs/dev-process/plans/`
- Story files under `docs/dev-process/plans/stories/`

## Technical Constraints

- Use the existing RealizeOS skill executor and prompt builder.
- Avoid adding a new CLI entrypoint in v1.
- Keep the cross-system feature flag off globally; use explicit shared workflows instead.
- Work with mixed source inputs and manual records before any live adapter work.

## Success Metrics

- Both systems load correctly from config and auto-discover the new agents.
- Shared investment dashboard skill is available from both systems.
- Daily brief and rebalance workflows can run using KB context plus web tools.
- Tests cover shared skill loading and richer skill-step context handling.

## Open Questions

- Which broker/data adapter is the first candidate after v1 stabilization.
- How approval events should eventually persist beyond markdown and conversation history.
