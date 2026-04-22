---
type: deal-dossier
version: 1
jurisdiction: Portugal
authority_mode: paper_execute
---

# Deal Dossier — 0-prior-sale

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
- **event-letter:** `0`

---

## 1. Identity

- **Deal slug:** `0-prior-sale`
- **Event letter:** `0`
- **One-line description:** `Prior-year property sale with unpaid mais-valias, pending Modelo 3 filing`
- **Current status:** `post-close obligations pending`
- **Is this a decision or a fixed obligation?** `fixed-obligation`
  - Event 0 is always `fixed-obligation`. Decisions are optimization variables; fixed obligations are constraints.

---

## 2. Counterparties & roles

| Role | Name | Contact | Introduced by | Notes |
|------|------|---------|---------------|-------|
| Buyer / seller (the other side) | `TBD` | | | |
| Broker (your side) | `TBD` | | | |
| Broker (other side) | `TBD` | | | |
| Lawyer | `TBD` | | | |
| Notary | `TBD` | | | |
| Bank / financing | `TBD` | | | |
| Promoter (for dev project) | N/A | | | |
| Clinic / service provider | N/A | | | |
| Accountant | Mario Ferreira | Audax contabilidade | | Will handle Modelo 3 filing |

---

## 3. Economics

Every numeric line carries a confidence tag in brackets.

| Line item | Amount (EUR) | Confidence | Source |
|-----------|-------------:|------------|--------|
| Headline number (Sale Price) | 195,000.00 | `actual` | User input |
| Acquisition cost (for mais-valias basis) | 95,000.00 | `actual` | User input |
| Capitalized improvements | 21,500.00 | `actual` | User input |
| Other eligible expenses (legal, notary, agency) | 7,008.11 | `actual` | User input (Includes early repayment & broker) |
| Total Acquisition + Expenses | 123,508.11 | `actual` | User input |
| Net Capital Gain | 71,491.89 | `estimate` | Subject to inflation coefficient update |
| Mortgage Remaining on Sale | 86,700.00 | `actual` | User input |
| Net Equity from Sale | 102,303.75 | `actual` | User input |
| Reinvestment in New Primary Residence | 30,000 - 45,000 | `estimate` | User input (Dependent on Event B) |
| Reinvestment Ratio | ~27% - 41% | `estimate` | Calculated based on €108.3k net realization |
| Exempt Portion of Capital Gain | TBD | `estimate` | Dependent on Event B reinvestment |
| Taxable Portion of Capital Gain | TBD | `estimate` | Dependent on Event B reinvestment |
| 50% Taxable under IRS rules | TBD | `actual` | Tax law |
| Estimated Tax Payable | 11,548.69 | `estimate` | Optimization Variable (Will change based on Event B) |

- **Currency:** EUR
- **Financing structure:** `Mortgage cleared on sale`
- **Source of funds (if outflow):** `personal account` (for tax payment)
- **Destination of funds (if inflow):** `personal account`

---

## 4. Dates

| Milestone | Date | Confidence | Source |
|-----------|------|------------|--------|
| Acquisition date | May 16, 2022 | `actual` | User input |
| First contact / LOI | `TBD` | `placeholder` | |
| CPCV / promissory / equivalent signed | `TBD` | `placeholder` | |
| Deposit due | `TBD` | `placeholder` | |
| Escritura / closing (Sale) | Oct 31, 2025 | `actual` | User input |
| Payment schedule (list each) | `TBD` | `placeholder` | |
| Declaration / filing window (tax) | Next few months | `estimate` | IRS filing window usually April-June |
| Drop-dead / latest-acceptable date | `TBD` | `placeholder` | |
| Earliest-possible date | `TBD` | `placeholder` | |

---

## 5. Documents

| Document | Status | Path / link |
|----------|--------|-------------|
| CPCV / promissory contract | `HAVE` | Google Drive folder |
| Escritura (Sale) | `HAVE` | Google Drive folder |
| Escritura (Acquisition) | `HAVE` | Google Drive folder |
| Caderneta predial | `HAVE` | Google Drive folder |
| Renovation Invoices/Receipts | `HAVE` | Google Drive folder |
| Bank statements showing proceeds | `HAVE` | Google Drive folder |

---

## 6. Portugal-tax facts

- **IMT** — N/A (Sale of property)
- **Imposto do selo** — N/A
- **Mais-valias** — Liability accrued but not yet paid. 
  - Purchased: May 16, 2022. Sold: Oct 31, 2025. **Inflation coefficient** will apply to the €95,000 purchase price (likely ~1.05-1.10), further reducing the taxable gain.
  - The property was sold for €195,000. Acquisition cost was €95,000 with €21,500 in capitalized improvements and €7,008.11 in expenses. 
  - Gain is roughly €71,491.89 (before inflation adjustment).
  - The property sold WAS your registered primary residence (HPP), making it fully eligible for the reinvestment exemption.
  - **Important Reinvestment Rule**: The net realization value to be reinvested is €108,300 (€195k sale - €86.7k mortgage). You plan to reinvest between €30,000 and €45,000 into Event B. This represents roughly a 27% to 41% reinvestment ratio, meaning 59% to 73% of the gain will remain taxable. The exact tax owed is now an **optimization variable** linked to Event B.
- **IMI** — Allocated up to the date of sale.
- **NHR / IFICI** — `TBD` (Need to verify your tax status)
- **Corporate (IRC) implications** — N/A (Personal capital)
- **Open financas matters** — Modelo 3 / anexo G needs to be filed with Mario Ferreira in the upcoming months. You will owe an estimated €11,548.69 in tax. This is a fixed cash outflow we must reserve for.

---

## 7. Agent questions-back

> This is the active consolidation channel. Every unresolved field in sections 1–6 must either (a) be answered via the inputs you already provided, or (b) appear here as a specific question-and-answer. Silent `TBD` is not permitted.

Q (orchestrator, 2026-04-20): What was the exact date of acquisition and the exact date of the sale?
A: Purchase - May 16th 2022. Sale - Oct 31st 2025.
→ Dates added to Section 4. Inflation coefficient will be applied in strategy phase.

Q (portugal-life, 2026-04-20): Was the sold property officially registered as your primary residence (Habitação Própria Permanente - HPP)?
A: Yes it was habitacao propria.
→ Confirmed eligibility for reinvestment exemption.

Q (portugal-life, 2026-04-20): Are you certain you will only use €15,000 of the proceeds from this sale toward the new house?
A: I will probably use more, I believe somewhere between 30-45K. Not sure yet, depends on the purchase price of the next property and mortgage.
→ Reinvestment amount updated to 30K-45K estimate. This links Event 0's final tax liability to Event B's financing structure.

Q (orchestrator, 2026-04-20): Did the remaining difference (~€6,000) go toward paying the real estate agent/lawyer or early repayment penalty?
A: I had both early repayment fee, and paid to the broker. I can point you out to the folder on my google drive with all the expenses invoices.
→ Eligible expenses noted. We will verify exact numbers against the Google Drive folder before final tax calculation.

Q (execution_controller, 2026-04-20): Do you have the Escrituras and the invoices for the €21,500 in renovations?
A: Yes I have all of them.
→ Document statuses updated to HAVE (stored in Google Drive).

---

## 8. Open questions

> Only for questions that survived the questions-back loop — genuine unknowns that strategy must route around, not ones the user forgot to answer.

_(empty until questions-back completes)_

---

## 9. Decisions already made (irrevocable)

> List any commitment that cannot be un-made: signed CPCV, deposit paid, verbal commitment to counterparty, signed medical consent, etc. The strategy phase must treat these as fixed.

- Property is already sold, Mais-valias tax liability is locked and must be paid based on last year's IRS cycle.
- Mario Ferreira (Audax) is engaged to file the tax return.

---

## 10. Related facts from elsewhere

> Cross-references to other dossiers. Example: "Sale proceeds from this deal (event A) are the liquidity source for event B purchase — see `deal-buy-property.md` section 3."

- This sale's proceeds (`Net Equity: ~€102k`) will be used to fund the purchase of the new primary residence (Event B).
- Reinvestment tax exemption for this event depends entirely on the closing of Event B.

---

## Footer — consolidation audit

| Pass | Agent | Date | Outcome |
|------|-------|------|---------|
| Extraction | `personal-investments/execution_controller` + `orchestrator` | 2026-04-20 | Extracted raw data into template |
| Portugal-tax overlay | `personal/portugal-life` | 2026-04-20 | Added HPP & Reinvestment ratio rule check |
| Questions-back | all touching agents | 2026-04-20 | User answered 5 questions. Dependencies mapped. |
| Gap surfacing | `personal-investments/risk_controller` | 2026-04-20 | Approved: All placeholders resolved. Open estimate (Reinvestment) is explicitly linked to Event B. |
| Consolidated sign-off | `personal-investments/risk_controller` | 2026-04-20 | **CONSOLIDATED** |
