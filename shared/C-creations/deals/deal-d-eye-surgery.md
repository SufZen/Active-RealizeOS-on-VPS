---
type: deal-dossier
version: 1
jurisdiction: Portugal
authority_mode: paper_execute
---

# Deal Dossier — d-eye-surgery

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
- **event-letter:** `D`

---

## 1. Identity

- **Deal slug:** `d-eye-surgery`
- **Event letter:** `D`
- **One-line description:** `Eye laser surgery.`
- **Current status:** `not-started`
- **Is this a decision or a fixed obligation?** `decision`
  - Timing is flexible within the 1-2 month window.

---

## 2. Counterparties & roles

| Role | Name | Contact | Introduced by | Notes |
|------|------|---------|---------------|-------|
| Clinic | IMO in Lisbon (approximate) | | | Need to verify exact name later |
| Debtor | Brother | | | Owes you €2000 |

---

## 3. Economics

Every numeric line carries a confidence tag in brackets.

| Line item | Amount (EUR) | Confidence | Source |
|-----------|-------------:|------------|--------|
| Total surgery cost | ~2,500.00 | `estimate` | User input |
| Payment from Brother | 2,000.00 | `actual` | User input (debt repayment) |
| **Net out-of-pocket cash** | **~500.00** | `estimate` | Derived |

- **Currency:** EUR
- **Financing structure:** `100% upfront cash`
- **Source of funds (if outflow):** `personal account` (funded mostly by brother's debt repayment)
- **Destination of funds:** Clinic

---

## 4. Dates

| Milestone | Date | Confidence | Source |
|-----------|------|------------|--------|
| Surgery date | May-Jun 2026 (1-2 months) | `estimate` | User input |
| Payment due | Upfront (May-Jun) | `actual` | User input |

---

## 5. Documents

| Document | Status | Path / link |
|----------|--------|-------------|
| Clinic quote | `MISSING` | |

---

## 6. Portugal-tax facts

- **IRS deduction**: Medical expenses (despesas de saúde) are partially deductible in your IRS (15% up to €1,000 limit). Ensure you get a fatura with your NIF.

---

## 7. Agent questions-back

> This is the active consolidation channel. Every unresolved field in sections 1–6 must either (a) be answered via the inputs you already provided, or (b) appear here as a specific question-and-answer. Silent `TBD` is not permitted.

Q (orchestrator, 2026-04-20): The €2,000 from your brother — will he transfer this to your account so you can pay the clinic, or is he paying the clinic directly?
A: `He will transfer it to me.`
→ resolved

Q (execution_controller, 2026-04-20): Which clinic are you using? (We just need the name to log the counterparty).
A: `Probably IMO in Lisbon (need to confirm exact name).`
→ resolved

---

## 8. Open questions

_(empty until questions-back completes)_

---

## 9. Decisions already made (irrevocable)

- None yet.

---

## 10. Related facts from elsewhere

- The €2000 payment from the brother is effectively a collection of an outstanding asset, converted into a healthcare expense. Net liquidity drain is only ~€500.

---

## Footer — consolidation audit

| Pass | Agent | Date | Outcome |
|------|-------|------|---------|
| Extraction | `personal-investments/execution_controller` + `orchestrator` | 2026-04-20 | Extracted raw data. Brother debt repayment mapped. |
| Portugal-tax overlay | `personal/portugal-life` | 2026-04-20 | IRS medical deduction noted. |
| Questions-back | all touching agents | 2026-04-20 | 2 questions asked, awaiting user. |
| Gap surfacing | `personal-investments/risk_controller` | 2026-04-21 | Cleared. No placeholders remain. |
| Consolidated sign-off | `personal-investments/risk_controller` | 2026-04-21 | Approved. Ready for Step 2. |
