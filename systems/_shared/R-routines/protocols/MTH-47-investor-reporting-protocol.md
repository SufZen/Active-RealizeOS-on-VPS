# MTH-47 — Investor Reporting Protocol

> Shared Protocol | Used by: MC (ENT-05) | Agents: Finance Controller, Project Director, Capital & Sales

---

## Purpose

Governs the structured monthly reporting cycle to Limited Partners (LPs). Ensures transparent, timely, and accurate communication about project status, financials, and risks. Designed for SPV structures with external investors.

## When to Use

- Monthly management report cycle (by the 10th of each month)
- Quarterly deep-dive reports
- Ad-hoc investor updates (material events, milestone completions)
- Any formal communication with LP investors

## The Monthly Reporting Cycle

### Phase 1: Close the Month (Day 1-3)

**Actor:** Finance Controller

- Finalize all transactions for the previous month
- Reconcile bank statements against accounting records
- Update master financial tracker with final actuals
- Calculate Plan vs. Actual variance for all budget categories
- Flag any variance exceeding the entity's threshold (see context parameters)

**Output:** Closed month financials with variance analysis.

### Phase 2: Collect Pillar Inputs (Day 3-5)

Each functional area provides their section:

**From Project Director (Technical):**
- Milestones achieved this month
- Milestones planned but not achieved (with explanation and revised timeline)
- Key technical risks and current mitigations
- Next month's technical priorities
- External partner updates (contractors, consultants, authorities)

**From Capital & Sales:**
- Sales pipeline status (unit tracker update)
- New buyer interest, viewings, negotiations
- Contract activity (CPCVs signed, pending, expired)
- Agency or channel performance
- Market observations and comparable activity

**From Finance Controller:**
- Budget vs. Actual summary by category
- Cash position (opening balance, inflows, outflows, closing balance)
- Key financial metrics (spend rate, variance %, remaining budget)
- Upcoming significant payments (next 30-60 days)
- Tax/VAT status

### Phase 3: Compile Report (Day 5-7)

**Actor:** Finance Controller (with support from all pillars)

**Report structure:**

1. **Executive Summary** (2-3 sentences)
   - Overall project status (on track / attention needed / at risk)
   - Most significant development this month
   - Any flags requiring LP awareness

2. **Financial Overview**
   - Plan vs. Actual table (by category)
   - Cash position summary
   - Key financial metrics
   - Budget burn rate and remaining runway

3. **Technical Progress**
   - Milestone tracker (planned vs. achieved)
   - Timeline adherence assessment
   - Key photos or evidence of progress (if applicable)

4. **Sales Update**
   - Pipeline summary
   - Activity this month
   - Market context

5. **Risk Review**
   - Risk table: Description | Likelihood | Impact | Mitigation | Status
   - New risks identified this month
   - Risks resolved or downgraded

6. **Next Month Priorities** (Top 3)

7. **Decisions Required**
   - Items needing LP approval (with context and recommendation)
   - Deadline for decision (if time-sensitive)

### Phase 4: Internal Review (Day 7-8)

**Actor:** Project Director (or GP lead)

Review the complete report for:
- Accuracy of all sections (especially technical and financial alignment)
- Consistency between sections (no contradictions)
- Tone: professional, transparent, no surprises
- Decisions Required section is clear and actionable
- Nothing is hidden or downplayed

### Phase 5: Deliver to LP (Day 8-10)

**Actor:** Capital & Sales (or designated LP liaison)

- Send final PDF report via agreed channel (email, shared drive)
- Include any supporting documents referenced in the report
- Propose date/time for monthly review call (within 5 business days)

### Phase 6: LP Review Call (Day 10-15)

**Actor:** Full GP team + LP

- Walk through report section by section
- Answer LP questions thoroughly
- Discuss items requiring approval
- Agree on action items with owners and deadlines
- Duration: 45-60 minutes

### Phase 7: Log & File

**Actor:** Finance Controller / System

- Report PDF filed in designated document storage
- Decisions logged in M-memory/decisions.md
- Action items tracked in project management tool
- Call notes documented and filed

---

## Entity-Specific Context

### MC / Arena Habitat (ENT-05)
```yaml
lp: "Zodiaco (Eldad) — 67% LP"
gp: "Realization — 33% GP"
report_deadline: "10th of each month"
call_deadline: "15th of each month"
variance_threshold: "2.5% — exceeding requires LP notification"
approval_threshold: "10,000 EUR — requires LP approval"
bank: "NovoBanco"
filing: "Google Drive: 02_Financial/Monthly Reports/"
decisions_log: "M-memory/decisions.md"
action_tracking: "ClickUp"
team_roles:
  finance_controller: "Roy — financials, bank reconciliation, report compilation"
  project_director: "Asaf — technical milestones, contractor coordination, internal review"
  capital_sales: "Meirav — sales pipeline, LP communication, report delivery"
```

## Quality Checklist

Before sending to LP:

- [ ] All numbers reconciled against bank statements
- [ ] Every variance explained (cause + remediation if negative)
- [ ] Technical milestones reflect reality, not aspiration
- [ ] Sales data matches pipeline tracker
- [ ] Risks are specific to this month and project
- [ ] Decisions required are clearly stated with context and recommendation
- [ ] Report sent by deadline
- [ ] Review call scheduled by deadline
- [ ] Tone is professional and transparent throughout
- [ ] No surprises — anything material was pre-communicated

---

> Status: active
> Last updated: 2026-02-10
