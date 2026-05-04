---
type: foundation
scope: shared
purpose: Master strategic plan governing the operator's RealizeOS deployment as of May 2026
last_updated: 2026-05-04
supersedes: ad-hoc previous plans
---

# Master Strategic Plan v2

## Operator profile and stack reality

- **Operator:** Asaf Eyzenkot (Suf Zen brand)
- **Multiple ventures:** see `realize-os.yaml` and the ecosystem dashboard
- **Lifestyle:** nomadic, splitting between Setúbal (PT) and Milan (IT)
- **Deploy stack:** Hetzner VPS + Coolify + this RealizeOS engine + 22+ MCP integrations
- **Plan tier:** 5 routine slots (constraint that drives the routines architecture)

## Architectural commitments (locked)

1. **HITL via single Telegram channel.** All approvals route through "Realization Approvals" within the existing Realization Ecosystem Group, using the existing SufZ bot. Critical alerts only on a separate "Realization Critical" channel.

2. **No ClickUp dependency.** Operator does not maintain ClickUp. Truth sources: Gmail, Fireflies, RealizeOS, Drive, GitHub, social. ClickUp is a "use-when-needed" tool for kanban-style team work, not a system of record.

3. **Italy work removed from content routines.** MioLiving partnership stays as a deal-pipeline branch; no Italy-specific marketing.

4. **Marketing calendar = Suf Zen brand spine + each venture plugged in.** Suf Zen drives credibility/gravity; ventures cross-link.

5. **Weekends genuinely free.** No Telegram traffic Saturday or Sunday. Slot schedule designed around this.

## High-priority pre-launch projects

### Investment Intelligence System (Phase 2.5 — high priority)
- **Status:** Foundation in build
- **Dependencies blocking launch:**
  1. IPS draft (personal + company treasury) — see `systems/personal-investments/F-foundations/ips.md`
  2. Position ledger source-of-truth (IBKR Web API + manual Revolut)
  3. LiteLLM routing config on VPS for premium models on investment agents
  4. Risk Controller daily script
  5. CIO weekly review flow
  6. ROI monitoring dashboard
  7. Researcher meta-agent
  8. Paper-trade phase (4-8 weeks) before real money
- **Model choice:** Claude Opus 4.7 only (no parallel cross-validation in v1; revisit if alpha justifies cost)
- **Estimated monthly inference cost:** ~$15/mo
- **ROI gate:** if monthly spend > paper-trade alpha for 3 consecutive months → automatic pause and review
- **Detail spec:** `systems/personal-investments/B-brain/account-monitoring-spec.md`

### Realization AI Adoption (new service launch)
- **Status:** Pre-launch
- **What it is:** Custom AI adoption for solopreneurs and small businesses (≤20 people)
- **Roles:** Asaf = Business Architect & Delivery Lead; Meirav Gonen = Client Manager & Service Lead
- **ICP segments:** solo professionals/clinics, real estate agencies, architecture firms, small RE developers, service agencies
- **Offer:** Free 30-min discovery → €280+VAT 2hr Discovery & Roadmap session (with take-home roadmap doc + 7-day money-back) → on-demand €280 implementation sessions
- **Marketing channels:** LinkedIn (HE+EN), Instagram (HE), Facebook (HE), X (Twitter), plus Burtucala FB groups + Newsletter for high-intent crossover
- **Detail spec:** `systems/realization-il/F-foundations/ai-adoption-service.md`

### Dashboard expansion (replaces ClickUp idea)
- **Target:** `dashboard.realization.co.il` — currently doesn't exist (DNS + Coolify deploy needed)
- **Scope beyond ecosystem/roadmap:** KPIs panel, deals view, projects view, decision queue (Telegram approvals mirrored), per-venture activity feed
- **Source-of-truth manifest:** RealizeOS state, ClickUp (when used), Coolify API, Drive recent changes, GitHub commits, Fireflies titles, social activity

## Foundation order (sequenced for fastest value)

| # | Foundation | Time | Unlocks |
|---|---|---|---|
| 1 | Telegram approvals channel ("Realization Approvals" in existing group, SufZ bot configured) | ~30 min | All HITL |
| 2 | DNS + Coolify deploy of `dashboard.realization.co.il` | ~1h | Dashboard refresh routine |
| 3 | Master marketing calendar (Suf Zen spine + venture plug-ins) | 1h call | Content engine routines |
| 4 | n8n → Buffer integration scenario (Make subscription dropped) | ~30 min | Content publishing |
| 5 | AI Adoption ICP doc + offer one-pager + Roadmap template | ✅ shipped | AI Adoption marketing |
| 6 | RealizeOS evolution test run (manual end-to-end) | 30 min | Slot 1 evolution loop |
| 7 | Personal IPS — Asaf fills it in (Tue May 5 morning session) | 2h calendar block | Investment Phase 1 |
| 8 | IBKR Pro view-only username (Wed May 6 morning session) | 30-45 min | Investment ledger source |
| 9 | LiteLLM premium routing config on VPS | ~1h | Investment agents on Opus 4.7 |
| 10 | Risk Controller + CIO scripts | ~3h | Investment Phase 2 |
| 11 | Paper-trade phase | 4-8 weeks passive | Validates system |
| 12 | Company treasury IPS | 1h | Investment Phase 3 |
| 13 | Arena finance source wiring + decision log file | 1h | Workflow B |

Total active foundation time before all routines ship: ~12-15 hours across 3-4 weeks. Then 4-8 weeks paper-trade. Then real-money launch on investment.

## Recommended enable order for the 5 routine slots

1. **Week 1:** Slot 1 partial (just RealizeOS Evolution + Meeting distillation) + Slot 5 (Monday Week Launch)
2. **Week 2:** Slot 1 full (with content drafting once marketing calendar exists) + Slot 4 (Friday Week Wrap)
3. **Week 3:** Slot 3 (Pipeline Pulse) once Apollo + AI Adoption pipelines have content
4. **Week 4+:** Slot 2 (Investment) once IPS is filled in and IBKR connection works

## Identity statement

This system serves Asaf Eyzenkot's role as a **founder, venture architect, and operator across multiple ventures and geographies**. It is not a passive assistant — it is the operating layer that turns scattered work into compounding leverage. The operator's role is approver and decision-maker, not operator-of-routines.
