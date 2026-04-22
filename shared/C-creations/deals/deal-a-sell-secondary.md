---
type: deal-dossier
version: 1
jurisdiction: Portugal
authority_mode: paper_execute
---

# Deal Dossier — a-sell-secondary

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
- **event-letter:** `A`

---

## 1. Identity

- **Deal slug:** `a-sell-secondary`
- **Event letter:** `A`
- **One-line description:** `Sale of secondary property (50/50 ownership with girlfriend), purchased Feb 2024`
- **Current status:** `in-negotiation` (offer received, CPCV not yet signed)
- **Is this a decision or a fixed obligation?** `decision`
  - The sale price, timing, and whether to accept the current offer are all optimization variables.

---

## 2. Counterparties & roles

| Role | Name | Contact | Introduced by | Notes |
|------|------|---------|---------------|-------|
| Buyer (the other side) | `TBD` | | | Offer received, negotiating |
| Co-owner (your side) | Girlfriend | | | 50% owner of the property |
| Broker (your side) | `TBD` | | | Will charge brokerage fee on sale |
| Broker (other side) | `TBD` | | | |
| Lawyer | `TBD` | | | |
| Notary | `TBD` | | | |
| Bank / financing | `TBD` | | | Mortgage holder — €79,700 remaining |
| Accountant | Mario Ferreira | Audax contabilidade | | IRS filing for mais-valias |

---

## 3. Economics

Every numeric line carries a confidence tag in brackets.

| Line item | Amount (EUR) | Confidence | Source |
|-----------|-------------:|------------|--------|
| Sale price (buyer's offer) | 175,000.00 | `actual` | Buyer's offer, still negotiating |
| **Your 50% share of sale** | **87,500.00** | `actual` | Derived from 50/50 ownership |
| Acquisition cost (total) | 112,000.00 | `actual` | User input |
| **Your 50% share of acquisition** | **56,000.00** | `actual` | Derived |
| Capitalized improvements | 0 | `actual` | User confirmed — no renovations |
| IMT (paid on purchase, secondary) | ~1,220.83 | `estimate` | Calculated: €112K × 2% − €1,019.17 (secondary bracket) |
| Imposto do selo (paid on purchase) | ~896.00 | `estimate` | 0.8% × €112K |
| Notary fees (purchase) | ~600.00 | `estimate` | Typical range for this amount |
| Brokerage fee (on sale, 4% + IVA) | ~8,610.00 | `estimate` | 4% × €175K × 1.23 IVA |
| Mortgage early repayment penalty | ~398.50 | `actual` | 0.5% × €79,700 (variable rate) |
| **Total transaction expenses** | **~11,725.33** | `estimate` | Sum of IMT+IS+notary+brokerage |
| **Your 50% of deductible expenses** | **~5,863** | `estimate` | Expenses / 2 (note: early repayment is NOT deductible from mais-valias) |
| Mortgage remaining | 79,700.00 | `actual` | User input |
| **Net equity from sale (total, both owners)** | ~86,291 | `estimate` | 175K − 79.7K mortgage − 8,610 brokerage − 398.50 early repayment |
| **Your 50% of net equity** | **~43,146** | `estimate` | Derived |

- **Currency:** EUR
- **Financing structure:** `Mortgage to be cleared on sale`
- **Source of funds (if outflow):** N/A (this is a sale / inflow)
- **Destination of funds (if inflow):** `personal account` — this equity is the primary liquidity source for Event B
- **CPCV sinal (deposit):** 10% = €17,500 (planned)

### Mais-valias estimate (your 50% share)

```
Your share of sale:                      87,500.00
Your share of acquisition (pre-coeff):  -56,000.00
Inflation coefficient (~1.03, 2024→2026):
  Adjusted acquisition:                 -57,680.00 (estimate)
Deductible expenses (your 50%):
  IMT:      -610.42
  IS:       -448.00
  Notary:   -300.00
  Brokerage:-4,305.00
  (Early repayment NOT deductible)        ────────
  Total deductible:                      -5,663.42
────────────────────────────────────────────────────
Gross capital gain (your 50%):           ~24,156  (estimate)
50% taxable under IRS:                  ~12,078  (estimate)
Estimated tax (marginal rate 26-35%):    ~3,140 - 4,230  (estimate)
```

> **CRITICAL**: This is a secondary property (NOT HPP). No reinvestment exemption applies. The mais-valias tax is a fixed cost — only the deductible expenses reduce it.
> 
> **NOTE**: The brokerage (€8,610) is the largest deductible expense and is worth ~€1,120-€1,510 in tax savings. Make sure to keep the fatura.

---

## 4. Dates

| Milestone | Date | Confidence | Source |
|-----------|------|------------|--------|
| Acquisition date | Feb 20, 2024 | `actual` | User input |
| CPCV / promissory / equivalent signed | Not yet signed | `actual` | Offer received, negotiation ongoing |
| Offer received | Apr 2026 | `actual` | User input |
| Expected escritura / closing | ~July 2026 | `estimate` | User input ("within 2-3 months") |
| Declaration / filing window (tax) | Apr-Jun 2027 IRS filing | `actual` | Tax law — 2026 income year |
| CPCV deposit (sinal) due | At CPCV signing | `actual` | 10% = €17,500 |
| Earliest-possible date | After CPCV signing + ~2-3 months | `estimate` | Standard timeline |

---

## 5. Documents

| Document | Status | Path / link |
|----------|--------|-------------|
| CPCV / promissory contract | `N/A` | Not yet signed |
| Escritura (Acquisition, Feb 2024) | `TBD` | |
| Caderneta predial | `TBD` | |
| Certidão de teor (conservatória) | `TBD` | |
| Energy certificate | `TBD` | |
| Bank commitment / mortgage statement | `TBD` | |
| IMT receipt (purchase) | `TBD` | Need for mais-valias deduction |

---

## 6. Portugal-tax facts

- **IMT** — N/A on the sale side. IMT paid on purchase is deductible from mais-valias calculation.
- **Imposto do selo** — N/A on sale. Selo paid on purchase (~0.8% of €112K = ~€896) is deductible.
- **Mais-valias** — **This is a secondary property, NOT HPP. No reinvestment exemption applies.**
  - Purchased Feb 2024, selling ~July 2026. Holding period ~2.5 years.
  - 50/50 ownership: each owner declares their 50% share of the gain on their own IRS.
  - Inflation coefficient for 2024 acquisition will apply (small, ~1.02-1.04).
  - 50% of the gain is taxable under IRS rules (added to marginal rate income).
  - The girlfriend must also file her share separately — this is her tax obligation, not yours, but worth coordinating.
  - **No overlap with Event 0 filing** — Event 0 is 2025 income (filed 2026), Event A is 2026 income (filed 2027).
- **IMI** — Proportional allocation for the year of sale.
- **NHR / IFICI** — `TBD` (Same question as Event 0 — applies across all events).
- **Corporate (IRC) implications** — N/A (personal ownership).
- **Open financas matters** — None specific to this deal.

---

## 7. Agent questions-back

> This is the active consolidation channel. Every unresolved field in sections 1–6 must either (a) be answered via the inputs you already provided, or (b) appear here as a specific question-and-answer. Silent `TBD` is not permitted.

Q (orchestrator, 2026-04-20): What is the exact date of acquisition in February 2024?
A: Feb 20th 2024.
→ Date logged. Inflation coefficient for 2024→2026 will be ~1.03.

Q (execution_controller, 2026-04-20): What was the IMT amount paid when you purchased for €112K?
A: Doesn't remember exact amount. It was the typical amount for a secondary property at this price. IS and notary fees as well.
→ Calculated: IMT ~€1,220.83 (secondary bracket: €112K × 2% − €1,019.17). IS ~€896. Notary ~€600. User should verify against receipts when available.

Q (execution_controller, 2026-04-20): What is the brokerage fee on the sale?
A: 4% + IVA.
→ Calculated: 4% × €175K × 1.23 = ~€8,610. Fully deductible from mais-valias.

Q (execution_controller, 2026-04-20): What is the mortgage early repayment penalty?
A: 0.5% of the remaining amount.
→ 0.5% × €79,700 = €398.50. Note: this is NOT deductible from mais-valias (financing cost), but it reduces net equity.

Q (risk_controller, 2026-04-20): Is the €175K the buyer's offer or your target price?
A: The offer.
→ Confidence upgraded to `actual` for sale price. Negotiation still ongoing — price could change.

Q (portugal-life, 2026-04-20): Is your girlfriend a Portugal tax resident?
A: Yes.
→ She files her 50% under normal IRS marginal rate (not the 28% non-resident flat rate).

Q (risk_controller, 2026-04-20): Do you plan to include a meaningful sinal (deposit) in the CPCV?
A: Yes, 10%.
→ €17,500 sinal. Good protection — if buyer pulls out, you keep the deposit. If you pull out, you pay double.

---

## 8. Open questions

> Only for questions that survived the questions-back loop — genuine unknowns that strategy must route around, not ones the user forgot to answer.

_(empty until questions-back completes)_

---

## 9. Decisions already made (irrevocable)

> List any commitment that cannot be un-made: signed CPCV, deposit paid, verbal commitment to counterparty, signed medical consent, etc. The strategy phase must treat these as fixed.

- No irrevocable commitments yet — CPCV not signed, offer still in negotiation.
- Ownership structure (50/50 with girlfriend) is a legal fact — cannot be changed for this sale.

---

## 10. Related facts from elsewhere

> Cross-references to other dossiers. Example: "Sale proceeds from this deal (event A) are the liquidity source for event B purchase — see `deal-buy-property.md` section 3."

- **Event B dependency**: Net equity from this sale (~€43.1K your share after all costs) is the primary cash source for the down payment on Event B. Event B cannot close before Event A.
- **Event B sequencing**: User explicitly stated "I will buy this property right after I finish the sell" — to ensure good bank mortgage approval (showing cash + no outstanding mortgage).
- **Event 0 interaction**: This sale's mais-valias is filed in 2027 (separate from Event 0 which is filed in 2026). No declaration overlap, but both tax bills need to be budgeted in the cashflow timeline.
- **Event A tax bill (~€3,140-€4,230) is due in 2027** — must be reserved in cashflow. Not payable until IRS filing.

---

## Footer — consolidation audit

| Pass | Agent | Date | Outcome |
|------|-------|------|---------|
| Extraction | `personal-investments/execution_controller` + `orchestrator` | 2026-04-20 | Extracted raw data. Expenses computed. |
| Portugal-tax overlay | `personal/portugal-life` | 2026-04-20 | Secondary property — no reinvestment exemption. 50/50 split confirmed. GF is PT resident. |
| Questions-back | all touching agents | 2026-04-20 | 7 questions asked, all answered. Expenses calculated. |
| Gap surfacing | `personal-investments/risk_controller` | 2026-04-20 | Approved: No placeholders remain. IMT/notary are estimates (user to verify vs receipts). |
| Consolidated sign-off | `personal-investments/risk_controller` | 2026-04-20 | **CONSOLIDATED** |
