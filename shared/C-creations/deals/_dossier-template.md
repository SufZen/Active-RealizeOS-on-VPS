---
type: deal-dossier-template
version: 1
jurisdiction: Portugal
authority_mode: paper_execute
---

# Deal Dossier — {{SLUG}}

> Canonical per-deal dossier. Copy this file as `deal-{slug}.md` in this directory and fill in every section. Missing data does not become a silent `TBD` — it becomes a question in the `Agent questions-back` section, answered by the user or escalated to `Open questions`.
>
> **Confidence tags** on every number: `actual` (from a document you supplied) / `estimate` (your best guess) / `placeholder` (literally made up — must be resolved before strategy phase). No `placeholder` may survive to Step 4 of the workflow.
>
> **Status header** (update as the dossier progresses):
> - `status: raw`        — raw input dumped, no extraction yet
> - `status: extracted`  — structured into template, confidence tags applied
> - `status: questioned` — agents have asked their questions, you have answered
> - `status: consolidated` — risk_controller has signed off on information quality; dossier is ready for strategy

- **status:** `raw`
- **last-updated:** `{{YYYY-MM-DD}}`
- **event-letter:** `{{0 | A | B | C | D | E …}}`

---

## 1. Identity

- **Deal slug:** `{{slug}}`
- **Event letter:** `{{0 / A / B / C / D / E+}}`
- **One-line description:** `{{e.g., "Sale of apartment in Setúbal, 2025 signing, mais-valias unpaid"}}`
- **Current status:** `{{not-started / in-negotiation / CPCV-signed / escritura-scheduled / closed / post-close obligations pending}}`
- **Is this a decision or a fixed obligation?** `{{decision | fixed-obligation}}`
  - Event 0 is always `fixed-obligation`. Decisions are optimization variables; fixed obligations are constraints.

---

## 2. Counterparties & roles

| Role | Name | Contact | Introduced by | Notes |
|------|------|---------|---------------|-------|
| Buyer / seller (the other side) | | | | |
| Broker (your side) | | | | |
| Broker (other side) | | | | |
| Lawyer | | | | |
| Notary | | | | |
| Bank / financing | | | | |
| Promoter (for dev project) | | | | |
| Clinic / service provider | | | | |
| Other | | | | |

---

## 3. Economics

Every numeric line carries a confidence tag in brackets.

| Line item | Amount (EUR) | Confidence | Source |
|-----------|-------------:|------------|--------|
| Headline number (price / ticket / quote) | | `actual / estimate / placeholder` | |
| Acquisition cost (for mais-valias basis) | | | |
| Capitalized improvements | | | |
| IMT | | | |
| Imposto do selo | | | |
| Notary fees | | | |
| Legal fees | | | |
| Broker commission | | | |
| Financing costs (interest, origination) | | | |
| Renovation / capex | | | |
| Other costs | | | |
| **Net cash impact** (signed: + inflow, − outflow) | | | |

- **Currency:** EUR (flag any exception explicitly)
- **Financing structure:** `{{all-cash / mortgage (amount, bank, rate, term) / seller-finance / equity+debt mix / N/A}}`
- **Source of funds (if outflow):** `{{personal account(s) / company account / mixed — to be decided in capital-routing step}}`
- **Destination of funds (if inflow):** `{{personal account / company account / escrow}}`

---

## 4. Dates

| Milestone | Date | Confidence | Source |
|-----------|------|------------|--------|
| First contact / LOI | | | |
| CPCV / promissory / equivalent signed | | | |
| Deposit due | | | |
| Escritura / closing | | | |
| Payment schedule (list each) | | | |
| Capital-call schedule (for dev project) | | | |
| Declaration / filing window (tax) | | | |
| Drop-dead / latest-acceptable date | | | |
| Earliest-possible date | | | |

---

## 5. Documents

| Document | Status | Path / link |
|----------|--------|-------------|
| CPCV / promissory contract | `HAVE / MISSING / N/A` | |
| Escritura | | |
| Caderneta predial | | |
| Certidão de teor (conservatória) | | |
| Energy certificate | | |
| Planning / licensing docs | | |
| Bank commitment letter | | |
| Financas declarations (relevant year) | | |
| Counterparty due-diligence file | | |
| Clinic quote / service agreement | | |
| Other | | |

---

## 6. Portugal-tax facts

- **IMT** — rate bracket, taxable basis, payer, due date.
- **Imposto do selo** — rate, basis, due date.
- **Mais-valias** — holding period, indexed acquisition cost, improvements deductible, inflation coefficient, taxable portion, expected tax amount, **already accrued but not yet paid?** (key for event 0).
- **IMI** — current IMI status, proportional allocation for the year of sale/purchase.
- **NHR / IFICI** — residency status, which regime applies, whether the event straddles a year boundary that affects attribution.
- **Corporate (IRC) implications** — only if the deal may route through the company: tax on gains, dividend extraction cost if extracting later, deductibility of costs.
- **Open financas matters** — anything unresolved on the AT portal that might interact with this deal.

---

## 7. Agent questions-back

> This is the active consolidation channel. Every unresolved field in sections 1–6 must either (a) be answered via the inputs you already provided, or (b) appear here as a specific question-and-answer. Silent `TBD` is not permitted.
>
> Format:
> ```
> Q (<agent>, YYYY-MM-DD): <specific question>
> A: <your answer, with confidence tag>
> → <what the agent does with the answer, or "promoted to Open questions because …">
> ```

_(empty — agents will append during Step 1 extraction and gap-surfacing)_

---

## 8. Open questions

> Only for questions that survived the questions-back loop — genuine unknowns that strategy must route around, not ones the user forgot to answer.

_(empty until questions-back completes)_

---

## 9. Decisions already made (irrevocable)

> List any commitment that cannot be un-made: signed CPCV, deposit paid, verbal commitment to counterparty, signed medical consent, etc. The strategy phase must treat these as fixed.

_(empty — fill in as applicable)_

---

## 10. Related facts from elsewhere

> Cross-references to other dossiers. Example: "Sale proceeds from this deal (event A) are the planned liquidity source for event B purchase — see `deal-buy-property.md` section 3."

_(empty — fill in as applicable)_

---

## Footer — consolidation audit

| Pass | Agent | Date | Outcome |
|------|-------|------|---------|
| Extraction | `personal-investments/execution_controller` + `orchestrator` | | |
| Portugal-tax overlay | `personal/portugal-life` | | |
| Questions-back | all touching agents | | |
| Gap surfacing | `personal-investments/risk_controller` | | |
| Consolidated sign-off | `personal-investments/risk_controller` | | |
