---
type: deal-dossier
version: 1
jurisdiction: Portugal
authority_mode: paper_execute
---

# Deal Dossier — c-dev-project

> Canonical per-deal dossier. Copy this file as `deal-{slug}.md` in this directory and fill in every section. Missing data does not become a silent `TBD` — it becomes a question in the `Agent questions-back` section, answered by the user or escalated to `Open questions`.
>
> **Confidence tags** on every number: `actual` (from a document you supplied) / `estimate` (your best guess) / `placeholder` (literally made up — must be resolved before strategy phase). No `placeholder` may survive to Step 4 of the workflow.
>
> **Status header** (update as the dossier progresses):
> - `status: raw`        — raw input dumped, no extraction yet
> - `status: extracted`  — structured into template, confidence tags applied
> - `status: questioned` — agents have asked their questions, you have answered
> - `status: consolidated` — risk_controller has signed off on information quality; dossier is ready for strategy

- **status:** `consolidated`
- **last-updated:** `2026-04-20`
- **event-letter:** `C`

---

## 1. Identity

- **Deal slug:** `c-dev-project`
- **Event letter:** `C`
- **One-line description:** `Investment in real estate development company (Escorpiao Diplomado LDA) where you are a co-promoter.`
- **Current status:** `in-progress` (initial investment made, rest due this week)
- **Is this a decision or a fixed obligation?** `decision`
  - The remaining payment is a decision, though practically a commitment. Conduit (personal vs company) is an optimization variable.

---

## 2. Counterparties & roles

| Role | Name | Contact | Introduced by | Notes |
|------|------|---------|---------------|-------|
| Promoter / Project Co. | Escorpiao Diplomado LDA | | | User is a co-promoter/partner |
| Partners | `TBD` | | | Co-investors in the LDA |
| Broker | N/A | | | |
| Lawyer | `TBD` | | | |
| Accountant | `TBD` | | | |

---

## 3. Economics

Every numeric line carries a confidence tag in brackets.

| Line item | Amount (EUR) | Confidence | Source |
|-----------|-------------:|------------|--------|
| Total committed ticket | 15,000.00 | `actual` | User input |
| Amount already invested | 1,500.00 | `estimate` | Derived |
| **Remaining to be paid (this week)** | 13,500.00 | `actual` | User input |
| Potential future investment | `TBD` | `estimate` | User: "might invest more later" |

- **Currency:** EUR
- **Financing structure:** `Equity (quotas) - user is seed investor & manager`
- **Source of funds (if outflow):** `Company (Realization Unipessoal LDA) — funded first via a €13.5K personal shareholder loan to the company`
- **Destination of funds (if inflow):** N/A

---

## 4. Dates

| Milestone | Date | Confidence | Source |
|-----------|------|------------|--------|
| Initial investment | Past | `actual` | User input |
| Remaining capital call | **This week (Apr 2026)** | `actual` | User input |
| Expected exit / return | ~2028 (2 years) | `estimate` | User input |

---

## 5. Documents

| Document | Status | Path / link |
|----------|--------|-------------|
| Investment agreement / LDA articles | `MISSING` | |
| Proof of previous transfers | `MISSING` | User has it documented |

---

## 6. Portugal-tax facts

- **Corporate (IRC) implications** — **CRITICAL OPTIMIZATION**: Since you are the sole owner of your company ("Realization"), you have a choice. You can invest in Escorpiao Diplomado LDA using your personal cash, OR you can invest via your company. 
  - If personal: any dividends/returns in 2 years are taxed at 28% (or marginal rate).
  - If company: inter-company dividends can often be exempt from tax under the Portuguese participation exemption (if holding requirements are met). We need to decide this in Step 4.

---

## 7. Agent questions-back

> This is the active consolidation channel. Every unresolved field in sections 1–6 must either (a) be answered via the inputs you already provided, or (b) appear here as a specific question-and-answer. Silent `TBD` is not permitted.

Q (orchestrator, 2026-04-20): Exactly how much of the €15,000 is **remaining to be paid this week**? (We need this for the immediate cashflow timeline).
A: `~13,500 EUR`
→ resolved

Q (investment_cio, 2026-04-20): How is the investment structured legally? Are you buying shares in the LDA (quotas), or providing a shareholder loan (suprimentos)? 
A: `Buying shares (quotas). I am also the manager of the company and part of the seed investors.`
→ resolved

Q (investment_cio, 2026-04-20): Will you fund this remaining amount from your **personal bank account** or your **company bank account**? (We can optimize this, but need to know where the initial payments came from to avoid mixed conduits).
A: `I will loan the amount to my company (Realization Unipessoal LDA) - a total amount of 13.5K. Then, I will invest in Escorpiao LDA through my company.`
→ resolved

---

## 8. Open questions

_(empty until questions-back completes)_

---

## 9. Decisions already made (irrevocable)

- Committed to the project as a co-promoter and manager.
- €15,000 total initial ticket is locked in.
- Decision made to route the €13.5K investment through Realization Unipessoal LDA.

---

## 10. Related facts from elsewhere

- Payment due this week competes for immediate liquid cash with everyday expenses, though it does not interfere with Event A/B which are months away.

---

## Footer — consolidation audit

| Pass | Agent | Date | Outcome |
|------|-------|------|---------|
| Extraction | `personal-investments/execution_controller` + `orchestrator` | 2026-04-20 | Extracted raw data. |
| Portugal-tax overlay | `personal/portugal-life` | 2026-04-20 | Flagged company vs personal conduit optimization. |
| Questions-back | all touching agents | 2026-04-20 | 3 questions asked, awaiting user. |
| Gap surfacing | `personal-investments/risk_controller` | 2026-04-21 | Cleared. No placeholders remain. |
| Consolidated sign-off | `personal-investments/risk_controller` | 2026-04-21 | Approved. Ready for Step 2. |
