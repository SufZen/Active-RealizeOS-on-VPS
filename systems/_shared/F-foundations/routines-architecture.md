---
type: foundation
scope: shared
purpose: 5-slot routine allocation for the Anthropic Routines feature, weekend-free design
last_updated: 2026-05-04
constraint: Anthropic plan allows 5 active routine slots; weekends must stay quiet
---

# Routines Architecture — 5-Slot Weekend-Free Design

## The constraint and the solution

Anthropic plan = 5 active routine slots, each with its own schedule. The operator's weekends must stay free of Telegram traffic. Solution: 5 carefully-designed slots with embedded "what to do today" decision logic, covering all repetitive operational work, with no slot overlap and no weekend pings.

## The 5 slots

### Slot 1 — Master Nightly Brief
- **Schedule:** Sunday–Thursday at 23:00 PT (5 nights/week — skips Fri+Sat)
- **Output:** Telegram morning digest delivered weekday mornings 07:00 PT
- **Always runs:**
  - Meeting distillation (yesterday's Fireflies → KB updates, content seeds, action items, deal/Arena signals)
  - RealizeOS Evolution Loop (`realizeos_run_evolution`, score top 3 changes, queue for approval)
  - Content engine (read marketing calendar + dynamic events + pipeline signals; draft content for next publishing day)
- **Conditional logic:**
  - **Sun nights:** AI Adoption prospecting batch + Burtucala newsletter compile + Suf Zen long-form draft
  - **Tue nights:** Dashboard refresh + Wed prospecting batch
  - **Thu nights:** Dashboard refresh + Fri prospecting batch + weekend content drafts (Fri/Sat/Sun coverage)

### Slot 2 — Investment Daily Sweep
- **Schedule:** Monday–Friday at 09:00 PT (markets closed weekends)
- **Output:** Silent unless action needed; alerts to "Realization Critical" channel
- **Always runs:** Risk Controller checks every IPS rule against latest ledger
- **Conditional:**
  - **Mondays:** CIO weekly portfolio review with rebalance proposals
  - **First trading day of month:** Researcher meta-agent reviews CIO calls vs realized outcomes

### Slot 3 — Pipeline Working Pulse
- **Schedule:** Tuesday + Thursday + Friday at 14:00 PT
- **Output:** Telegram approval queue (added to morning digest tail or sent as same-day update)
- **What it does:**
  - Scan Gmail for stalled threads (>5 days no response on AI Adoption / RE deals / partnerships)
  - Read Apollo sequences for follow-up due
  - Check Fireflies for action items not yet sent
  - Draft nudge messages (HE/EN, voice-tuned per recipient)
  - Surface 3-5 follow-up actions with one-tap approve

### Slot 4 — Friday Week Wrap
- **Schedule:** Fridays at 14:30 PT
- **Output:** Friday afternoon Telegram digest
- **What it does:**
  - Week-in-review across all ventures
  - Investor/partner updates owed (drafts ready)
  - Weekend reading queue
  - Suf Zen brand health metrics
  - Following week's Big 3 priorities surfaced

### Slot 5 — Monday Week Launch
- **Schedule:** Mondays at 08:30 PT
- **Output:** Monday morning Telegram digest (lands during operator's first coffee)
- **What it does:**
  - Calendar look-ahead next 7 days
  - Meeting prep cards for stake-bearing meetings (last conversation summary, pending items, decisions needed)
  - Delegation queue (drafts to Aldad, Meirav, Eden, GP team)
  - Burtucala newsletter final review (compiled Sunday night via Slot 1)
  - Week's Big 3 surfaced first thing
  - Personal time-blocking proposals

## Schedule summary

| Day | 08:30 | 09:00 | 14:00 | 14:30 | 23:00 |
|---|---|---|---|---|---|
| Sun | — | — | — | — | Slot 1 (prospects + newsletter compile) |
| Mon | Slot 5 | Slot 2 (Risk + CIO weekly) | — | — | Slot 1 (regular) |
| Tue | — | Slot 2 (Risk) | Slot 3 | — | Slot 1 (dashboard + Wed prospects) |
| Wed | — | Slot 2 (Risk) | — | — | Slot 1 (regular) |
| Thu | — | Slot 2 (Risk) | Slot 3 | — | Slot 1 (dashboard + Fri prospects + weekend drafts) |
| Fri | — | Slot 2 (Risk) | Slot 3 | Slot 4 (Wrap) | — *(weekend free)* |
| Sat | — | — | — | — | — *(silent)* |

## Coverage cross-check

| Originally planned routine | Where it lives now |
|---|---|
| Investment monitoring | Slot 2 |
| Content drafting | Slot 1 (always) + Slot 4 (review) |
| AI Adoption prospecting | Slot 1 (Sun/Tue/Thu nights → M/W/F morning queues) |
| RealizeOS Evolution | Slot 1 (always) |
| Dashboard refresh | Slot 1 (Tue/Thu nights) |
| Meeting distillation | Slot 1 (always) |
| Burtucala newsletter | Slot 1 Sunday compile + Slot 5 Monday review |
| Suf Zen brand health | Slot 4 weekly |
| Week prep | Slot 5 |
| RE deals | On-demand (Workflow A, not slotted) |
| Arena prep/sync | On-demand (Workflow B, not slotted) |

## Implementation handoff for the Routines feature

Each slot becomes one routine prompt with conditional logic at the top:

```
Today is {day_of_week}, {date}. Today's tasks:
- Always: [task list]
- If Monday: also do X
- If 1st of month: also do Y
- If Tue/Thu: also do dashboard refresh
[etc]
```

Each slot lists the MCP tools it needs upfront (RealizeOS, Fireflies, Apollo, Gmail, Drive, Calendar, web search). Each slot has clearly defined output destination (Telegram channel, Drive folder). Failures gracefully degrade.

The actual prompt drafts for each of the 5 slots are a follow-up artifact, not in this foundation document.
