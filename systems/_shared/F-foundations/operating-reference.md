---
type: foundation
scope: shared
purpose: Natural-language trigger reference + Telegram approval syntax for the operator
last_updated: 2026-05-04
---

# Operating Reference — Triggers & Approval Syntax

This file is the canonical reference for how Asaf interacts with the system across natural-language triggers, scheduled routines, and the Telegram HITL channel. Agents should reference this file when interpreting operator messages.

## Natural-language triggers (on-demand workflows)

Operators don't memorize exact phrases. The system accepts intent. Below are canonical examples — variants in operator's natural language should resolve to the same workflow.

### 🏢 New real estate deal
- **Canonical:** "New deal: [info]"
- **Variants:** "I got a property" / "Aldad sent me something" / "Look at this listing" / "Burtucala lead"
- **Routes to:** Workflow A (Universal RE Deal Pipeline, homed under `realization` system)
- **Action:** market_analyst initial memo → Telegram approval → branch by deal type

### 🏗️ Arena meeting prep
- **Canonical:** "Arena prep"
- **Variants:** "Arena meeting today" / "What's the Arena status" / "Brief me on Arena"
- **Routes to:** Workflow B pre-meeting mode (`arena` system)
- **Action:** Pull last decisions, your pending, Aldad's pending, decisions needed today, cashflow position

### 📊 Arena weekly sync
- **Canonical:** "Arena sync"
- **Variants:** "Arena weekly" / "Arena finance check"
- **Routes to:** Workflow B weekly sync (`arena` system, finance-controller agent)

### 📝 Arena decision logging
- **Canonical:** "Arena decision: [text]"
- **Variants:** "For Arena: we decided X" / "Arena update: [text]"
- **Routes to:** appends to `systems/arena/I-insights/decisions-log.md`

### 💼 AI Adoption prospect or session
- **Canonical:** "New AI Adoption lead: [info]" / "Discovery call done with [name]"
- **Routes to:** `realization-il` system, AI Adoption pipeline
- **Action:** Adds to pipeline; if paid session, drafts Roadmap doc via the `ai-adoption-roadmap` skill

### 🛠️ Site/infra commands
- **Canonical:** "Deploy [site]" / "Restart [site]" / "Status of [site]"
- **Routes to:** Coolify MCP (when wired)

## Scheduled routines (5-slot allocation)

Operator does NOT trigger these. They run on schedule. Output destination is the Telegram "Realization Approvals" channel (see HITL section below) on weekday mornings only.

| Slot | Schedule | Purpose |
|---|---|---|
| 1. Master Nightly Brief | Sun-Thu 23:00 PT | Meeting distillation + evolution loop + content drafts; weekday morning digest |
| 2. Investment Daily Sweep | Mon-Fri 09:00 PT | Risk Controller (silent unless breach); Mon=CIO weekly; 1st-of-month=Researcher |
| 3. Pipeline Working Pulse | Tue/Thu/Fri 14:00 PT | Stalled threads, follow-ups, existing pipeline movement |
| 4. Friday Week Wrap | Fri 14:30 PT | Week-in-review, partner updates owed, weekend reading, Big 3 |
| 5. Monday Week Launch | Mon 08:30 PT | Calendar look-ahead, meeting prep cards, week's Big 3 |

**Weekends are silent.** No Telegram traffic Saturday or Sunday.

For full architecture see `systems/_shared/F-foundations/routines-architecture.md`.

## HITL (Human-in-the-loop) via Telegram

All approvals route through one channel: **"Realization Approvals"** within the existing Realization Ecosystem Group. The existing **SufZ bot** (already configured) handles message delivery and reply parsing.

Critical real-time alerts (Investment IPS breaches only) go to a separate **"Realization Critical"** channel for immediate visibility.

### Morning approval reply syntax

Routine output is numbered. Operator replies with one of:

| Operator reply | System action |
|---|---|
| `approve 1,3,5` | Approves items 1, 3, 5 |
| `reject 2` | Drops item 2 |
| `reject 2: [reason]` | Drops with reason; meta-agent learns |
| `edit 4: [your text]` | Replaces draft with operator version |
| `defer 6` | Pushes to tomorrow's digest |
| `view 10` | Returns full details for that item |
| `approve all` | Only when operator has read everything |
| `pause routines` | Stops nightly runs (use during travel) |
| `resume routines` | Resumes |

### When operator phrasing is ambiguous

Don't guess. Ask one clarifying question via Telegram. Better than silently picking wrong.

## Sources of truth (no ClickUp)

The system reads from:
- **Gmail** — decisions, partner threads, status updates
- **Fireflies** — meeting transcripts and decisions
- **RealizeOS state** — system internal status
- **Google Drive** — recent file changes per venture folder
- **GitHub commits** — development activity heartbeat
- **Social media** — Suf Zen brand activity
- **Manual:** Revolut weekly export → Drive CSV
- **Deferred (not in scope):** WhatsApp

ClickUp is intentionally NOT a source of truth. Asaf doesn't maintain it consistently. Don't rely on it for state.

## File operations

Decisions logs, deals logs, and similar structured records are kept as YAML or markdown files in the appropriate venture's `I-insights/` directory. Examples:
- `systems/arena/I-insights/decisions-log.md`
- `systems/realization/I-insights/deals-log.yaml`
