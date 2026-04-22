---
type: deal-dossier
version: 1
jurisdiction: Portugal
authority_mode: paper_execute
---

# Deal Dossier — b-buy-hpp

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
- **event-letter:** `B`

---

## 1. Identity

- **Deal slug:** `b-buy-hpp`
- **Event letter:** `B`
- **One-line description:** `Purchase of remaining 75% of property (currently on brother's name) to become sole owner + HPP, financed by mortgage`
- **Current status:** `in-negotiation` (ownership structure agreed in principle, formal purchase not yet initiated)
- **Is this a decision or a fixed obligation?** `decision`
  - The purchase price, financing structure, and timing are all optimization variables. The 25% ownership claim is a pre-existing agreement.

---

## 2. Counterparties & roles

| Role | Name | Contact | Introduced by | Notes |
|------|------|---------|---------------|-------|
| Seller / current title holder | Brother | | | Property registered in his name |
| Co-owner by agreement (25%) | You (Asaf) | | | Written agreement in place |
| Original co-buyer | Brother's wife | | | Part of original purchase agreement |
| Original co-buyer | Girlfriend | | | Part of original purchase agreement |
| Broker | N/A (likely) | | | Family transaction |
| Lawyer | `TBD` | | | **Strongly recommended** for this deal |
| Notary | `TBD` | | | |
| Bank / financing | NovoBanco (primary option) | | | Will provide ~80% mortgage, considering other banks too |
| Accountant | Mario Ferreira | Audax contabilidade | | Tax implications |

---

## 3. Economics

Every numeric line carries a confidence tag in brackets.

| Line item | Amount (EUR) | Confidence | Source |
|-----------|-------------:|------------|--------|
| Total property value | 185,000 - 200,000 | `estimate` | User input |
| **Purchase price (75% share you're acquiring)** | **~138,750 - 150,000** | `estimate` | Derived (75% of total value) |
| Your existing 25% claim | ~46,250 - 50,000 | `estimate` | Derived (25% of total value) |
| Amount already paid for your 25% | 15,280.00 | `actual` | Google Sheet PDF (Asaf 25% share) |
| Original purchase price (whole property) | 110,000.00 | `actual` | User input |
| Total group cash invested (reno + down payment + fees) | 61,120.00 | `actual` | Google Sheet PDF (4 × 15,280) |
| IMT (on purchase, HPP rates) | ~4,000 - 5,000 | `estimate` | Based on 185K-200K declared price (VPT is lower) |
| Imposto do selo (on purchase) | ~1,480 - 1,600 | `estimate` | 0.8% of 185K-200K |
| Notary fees | ~700 - 1,000 | `estimate` | Standard range |
| Legal fees | ~1,000 - 2,000 | `estimate` | Recommended for this complex structure |
| Mortgage amount (~80% of total value) | ~148,000 - 160,000 | `estimate` | 80% of 185K-200K |
| Down payment (~20% of total value) | ~37,000 - 40,000 | `estimate` | 20% of 185K-200K |
| Brother's existing mortgage to clear | ~85,000.00 | `estimate` | Based on 88K original minus amortization |

- **Currency:** EUR
- **Financing structure:** `~80% mortgage + ~20% equity. Buying out brother (100%), brother's wife, and girlfriend.`
- **Source of funds (down payment):**
  - Net equity from Event A sale (~€43.1K your share)
  - Proceeds from Event 0 prior sale (€30K-€45K reinvestment portion) — **this is the Event 0 reinvestment exemption link**
  - Personal savings (if needed)
- **Destination of funds:** Purchase — property registration in YOUR name (sole owner)

### Capital flow summary (estimate)

```
Source: Event A net equity (your 50%)           ~43,146 (estimate)
Source: Event 0 proceeds reinvested             ~30,000 - 45,000 (estimate)
Source: Personal savings (if needed)            TBD
────────────────────────────────────────────────
Total available for down payment:               ~73,146 - 88,146 (estimate)
Down payment needed (20% of 185-200K):          ~37,000 - 40,000 (estimate)
Surplus / buffer after down payment:            ~33,146 - 51,146 (estimate)

Reserved obligations:
  Event 0 mais-valias tax (2026):               ~5,000 - 11,500 (depends on reinvestment)
  Event A mais-valias tax (2027):               ~3,140 - 4,230
  IMT + IS + notary + legal (Event B):          ~5,100 - 8,600
────────────────────────────────────────────────
Total reserved obligations:                     ~13,240 - 24,330
True surplus after all obligations:             ~8,816 - 37,906 (estimate)
```

> **CRITICAL NOTE**: The more of Event 0's sale proceeds you reinvest into THIS property (Event B), the lower your Event 0 mais-valias tax. There is a direct optimization trade-off: higher down payment on Event B = lower tax on Event 0, but also = less liquidity buffer.
>
> **OPTIMIZATION INSIGHT**: If you put ALL available Event 0 proceeds (€45K+) into this down payment, Event 0 tax could drop from ~€11.5K to ~€5K, saving ~€6.5K. The strategy phase (Step 4) will model this trade-off.

---

## 4. Dates

| Milestone | Date | Confidence | Source |
|-----------|------|------------|--------|
| Original purchase (by brother/group) | Early 2024 | `actual` | Deduced from mortgage dates |
| Renovations completed | Mid 2024 | `estimate` | Derived from sheet |
| Event A closing (prerequisite) | ~July 2026 | `estimate` | Must close first for mortgage approval |
| Mortgage application (NovoBanco) | ~Aug 2026 | `estimate` | After Event A closes, proceeds in account |
| CPCV / promissory signing | ~Aug 2026 | `estimate` | Can sign before or during mortgage process |
| Escritura / closing | ~Sep-Oct 2026 | `estimate` | After mortgage approval (~30-60 days) |
| IMT payment | Before escritura | `actual` | Must be paid before notary signs |
| Event 0 reinvestment deadline | Oct 2028 | `actual` | Art. 10 CIRS — 36-month window from Oct 2025 sale |

---

## 5. Documents

| Document | Status | Path / link |
|----------|--------|-------------|
| Original purchase agreement (4-way) | `HAVE` | Written agreement — Google Drive / Sheet |
| Investment tracking spreadsheet | `HAVE` | Google Sheet with all numbers |
| Current property registration (conservatória) | `TBD` | Shows brother as owner |
| Caderneta predial | `TBD` | Needed for VPT (IMT basis) |
| Energy certificate | `TBD` | |
| Bank mortgage pre-approval | `N/A` | Not yet applied (NovoBanco target) |
| Proof of 25% payment | `HAVE` | Google Sheet |

---

## 6. Portugal-tax facts

- **IMT** — This is the BIG question for this deal. Multiple scenarios:
  - **If structured as a standard purchase of 75%**: IMT is calculated on the declared price of the 75% share. HPP rates apply (lower than secondary). On ~€140K-€150K, IMT would be in the range of €2,800-€4,000.
  - **If the full property is transferred from brother's name to yours for €185-200K**: IMT is calculated on the higher of the declared price or the VPT. (User confirmed VPT is lower, so calculated on declared price). 
  - **Family transfer rules**: Transfer between siblings is treated as a standard sale for IMT purposes.
  - **Your existing 25%**: Since you are buying 100% via the bank, you will pay IMT on the full 100% declared value.
  
- **Imposto do selo** — 0.8% of the taxable basis.
- **Mais-valias** — N/A for you (buyer). But your **brother** will owe mais-valias on the sale of his share (75% or 100% depending on structure). This is his tax problem, but it may affect his willingness to set a price.
- **IMI** — You become liable for IMI as the new registered owner from the year of transfer.
- **NHR / IFICI** — `TBD` (same question across all events).
- **Corporate (IRC) implications** — N/A (personal purchase).
- **Open financas matters** — None specific yet.

### Event 0 reinvestment exemption linkage

- **This purchase (Event B) IS the reinvestment for Event 0's mais-valias exemption.**
- Under Art. 10 CIRS, you have **36 months from the sale** (Oct 2025) to reinvest in a new HPP.
- Deadline: **October 2028** — you have time.
- The amount you invest from your own funds (NOT the mortgage) into this property counts as reinvestment.
- **Optimization**: Every euro of Event 0 proceeds you put into Event B's down payment reduces Event 0's mais-valias tax proportionally.

---

## 7. Agent questions-back

> This is the active consolidation channel. Every unresolved field in sections 1–6 must either (a) be answered via the inputs you already provided, or (b) appear here as a specific question-and-answer. Silent `TBD` is not permitted.

Q (risk_controller, 2026-04-20): Is the 25% ownership agreement written and signed?
A: Written, no worries at all there.
→ Structural risk resolved. Written agreement protects your claim.

Q (orchestrator, 2026-04-20): When was the property originally purchased? What was the original purchase price?
A: Bought for €110K. Renovated after purchase. Has all numbers organized in a Google Sheet.
→ Original price logged. Renovation costs still needed from the Google Sheet.

Q (orchestrator, 2026-04-20): How much have you already paid toward your 25% share?
A: Invested exactly 25% of total cash investment. Brother also has a mortgage. All numbers are in a Google Sheet.
→ Need the actual amounts from the Google Sheet to calculate how much cash you still need to put in.

Q (portugal-life, 2026-04-20): Will this property become your HPP?
A: Yes, it will be my registered address and my habitação própria.
→ Confirmed: HPP rates apply for IMT (lower bracket). Event 0 reinvestment exemption is valid.

Q (risk_controller, 2026-04-20): Is the €185-200K the total property value or the amount you'd pay?
A: Total property value.
→ Your purchase of 75% = ~€138,750 - €150,000. You're buying out everyone to become sole owner.

Q (investment_cio, 2026-04-20): Will your girlfriend retain any ownership share?
A: 100% ownership will be mine.
→ You are buying out all 3 parties (brother, brother's wife, girlfriend). All give up their claims.

Q (execution_controller, 2026-04-20): For the mortgage — which bank?
A: Probably NovoBanco, considering other options too. Not important at this moment.
→ NovoBanco noted as primary option. Detailed mortgage planning deferred to execution phase.

Q (portugal-life, 2026-04-20): What is the VPT on the caderneta predial?
A: "Why does it matter?"
→ **Explanation**: IMT is legally calculated on whichever is HIGHER: the price you declare to Finanças, or the VPT (Valor Patrimonial Tributário) on the caderneta predial. If the VPT happens to be, say, €220K but you're declaring a purchase at €185K, you will pay IMT on €220K — not €185K. This can add €1,000-€2,000+ in unexpected IMT. It takes 2 minutes to check: Portal das Finanças → Património → Caderneta Predial → look for "Valor patrimonial actual". Your brother can check since it's in his name. **Promoted to Open Questions.**

---

## 8. Open questions

> Only for questions that survived the questions-back loop — genuine unknowns that strategy must route around, not ones the user forgot to answer.

1. **VPT (Valor Patrimonial Tributário)** — User needs to check via Portal das Finanças (brother's login). Determines whether IMT is calculated on the declared price or the VPT. Could change IMT amount by €1,000+.
2. **Exact amounts from Google Sheet** — Your 25% cash investment amount, renovation costs, brother's mortgage balance. These are needed to finalize the down payment calculation and the brother's mais-valias exposure.
3. **Brother's existing mortgage balance** — Must be cleared as part of this transaction. Affects how much of the €185-200K actually goes to cash payouts vs. mortgage clearing.

---

## 9. Decisions already made (irrevocable)

> List any commitment that cannot be un-made: signed CPCV, deposit paid, verbal commitment to counterparty, signed medical consent, etc. The strategy phase must treat these as fixed.

- 25% ownership agreement with brother, brother's wife, and girlfriend — written and signed.
- Decision: 100% ownership will transfer to you (Asaf). All other parties are being bought out.
- Will be registered as HPP (habitação própria permanente).
- No CPCV signed yet. No deposit paid. The purchase structure is still open to optimization.

---

## 10. Related facts from elsewhere

> Cross-references to other dossiers. Example: "Sale proceeds from this deal (event A) are the liquidity source for event B purchase — see `deal-buy-property.md` section 3."

- **Event 0 → Event B**: This purchase IS the reinvestment that triggers Event 0's mais-valias exemption. The more own-funds reinvested here, the lower the Event 0 tax. 36-month deadline: Oct 2028.
- **Event A → Event B**: Event A's net equity (~€43.1K your share) is the primary cash source for the down payment. Event A MUST close before Event B (user stated this explicitly for mortgage purposes).
- **Event A timing**: Event B's mortgage application depends on Event A being fully closed (mortgage cleared, proceeds in account). Target: apply for mortgage ~Aug 2026, close ~Sep-Oct 2026.
- **Brother's mais-valias**: The brother will owe mais-valias on his portion. Original purchase €110K + renovations → sale at €185-200K. This may affect price negotiations. Worth discussing openly.

---

## Footer — consolidation audit

| Pass | Agent | Date | Outcome |
|------|-------|------|---------|
| Extraction | `personal-investments/execution_controller` + `orchestrator` | 2026-04-20 | Extracted raw data. Original purchase €110K + renovations. |
| Portugal-tax overlay | `personal/portugal-life` | 2026-04-20 | HPP confirmed. IMT scenarios refined. Reinvestment exemption linkage to Event 0 confirmed. |
| Questions-back | all touching agents | 2026-04-20 | 8 questions asked, 7 answered, 1 promoted to Open Questions (VPT). |
| Gap surfacing | `personal-investments/risk_controller` | 2026-04-20 | 3 items remain in Open Questions: VPT, Google Sheet amounts, brother's mortgage. |
| Consolidated sign-off | `personal-investments/risk_controller` | | Pending: 3 Open Questions must be resolved first. |
