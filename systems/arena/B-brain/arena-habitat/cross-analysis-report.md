# Arena — SPV Cross-Analysis Report

> Prepared: 2026-03-26 | For: Asaf Eyzenkot, Eldad Stinbook
> Sources: Email thread (Tania Duarte), Investment Memorandum, Consolidated Business Model v5, Lawyer's contract documents, WhatsApp (Asaf-Eldad)

---

## Executive Summary

Cross-referencing 5 sources identified **3 critical gaps** that must be resolved before signing, and **12 data discrepancies** between documents. The critical gaps all relate to missing investor protections — the lawyer's corporate documents only cover company registration, not investment terms. A **pacto parassocial** (shareholders' agreement) is required to formalize the partnership economics.

---

## CRITICAL — Must Resolve Before Signing

### 1. Missing Investor Protections

| Source | What it covers |
|--------|---------------|
| Lawyer's docs (Ata 2, Cessao de Quotas, Contrato) | Corporate registration only — share transfer, capital increase, articles of association |
| Business model | Full 3-step waterfall, preferred returns, promote structure |
| WhatsApp (Eldad) | Explicit request for dissolution protections, exit definitions, manager controls |

**Gap:** No legally binding document covers the investment economics. The waterfall, preferred returns, exit mechanisms, and dissolution protections exist only in the business model spreadsheet and verbal agreements.

**Verbal agreement not yet documented:** "In case of not proceeding, Eldad keeps the land minus GP's investment."

**Resolution:** Draft a **Pacto Parassocial** (see separate requirements document). Request Tania to prepare it.

---

### 2. Manager Structure & Control

| Source | Position |
|--------|----------|
| Lawyer's docs | Asaf is sole manager (gerente) with single-signature bank authority |
| Eldad (WhatsApp) | Concerns about: manager replacement rights, dual-signature safeguards, asset protection |
| Business model | Silent on governance |

**Gap:** Sole-manager structure with single-signature authority gives GP full operational control with no LP safeguards.

**Resolution — address in pacto parassocial:**
- Dual-signature for bank transactions above 10,000
- LP (67%) can replace manager with cause (defined triggers: fraud, gross negligence, abandonment, material breach)
- Manager change requires 75% quota vote (already standard under Portuguese LDA law — Article 257 CSC)

---

### 3. Dissolution / Exit Terms Missing

| Source | Position |
|--------|----------|
| Lawyer's docs | Standard articles — dissolution per Portuguese law (unanimous or judicial) |
| Eldad (WhatsApp) | "What happens in case of dissolution?" / "Where are the points of no return?" |
| Business model | Waterfall applies at exit but no dissolution mechanics |

**Gap:** No document defines what happens if the project stops, if a partner wants out, or how assets are distributed at each phase.

**Resolution — define in pacto parassocial by project phase:**

| Phase | Scenario | Resolution |
|-------|----------|------------|
| Phase 1: Pre-land | Either party exits | Capital returned pro-rata |
| Phase 2: Post-land, pre-construction | GP exits | LP retains full land ownership |
| Phase 2: Post-land, pre-construction | LP exits | LP receives land value minus GP's documented sweat equity investment |
| Phase 3: During construction | Either party | No unilateral exit. Forced completion. Non-performing party loses promote/upside |
| Phase 4: Post-construction | Standard exit | Waterfall applies (capital return LIFO, preferred returns, promote split) |

---

## RESOLVED — Data Discrepancies

The **Consolidated Business Model v5** is the source of truth for all financial figures except the preferred return rate (kept at 10% per GP-LP agreement).

| # | Item | Presentation says | KB says | Business Model says | Resolution |
|---|------|-------------------|---------|---------------------|------------|
| 4 | Units | 10 | 10 | 11 (A-K) | **11 is correct.** Update all docs |
| 5 | Seed Pref Rate | 10% | 10% | 12% | **Keep 10%** per GP-LP agreement. Update business model |
| 6 | Total Revenue | 2,750,000 | N/A | 2,646,474 | **Business model correct** |
| 7 | Net Profit | 546,000 | N/A | 391,643 (after tax) | **Business model correct** |
| 8 | Equity IRR | 52.1% | N/A | 21.6% (Round 1 annual) | **Business model correct** |
| 9 | Construction cost | 1,300/sqm | 1,300/sqm | 1,450/sqm | **Business model correct: 1,450/sqm** |
| 10 | Timeline | 30 months | 30 months | 21 months | **Business model correct: 21 months** |
| 11 | Capital structure | Seed / Series A / Series B | Seed / Loan / Series A | Round 1-4 + Developer | **Business model correct.** Rounds 2-4 are mezzanine debt, not equity |
| 12 | Waterfall split | N/A | 67/33 (mirrors ownership) | 30% GP Promote / 70% LP | **Business model correct: 30/70 promote** |
| 13 | Round 1 cash | N/A | Implied 67/33 | Eldad 250K (94%) / Asaf 15K (6%) | **Both valid.** Company ownership (67/33) reflects Asaf's sweat equity (~46K equivalent) + 15K cash. Document in pacto parassocial |
| 14 | SPV Name | Marvelous Creations | Marvelous Creations | Escorpiao | **Escorpiao LDA is correct.** Pivot from Marvelous Creations due to Oded's divorce blocking share transfer |
| 15 | Governance thresholds | N/A | <5K / 5-10K / >10K | N/A | **See recommended mechanism below** |

---

## SPV Name Change: Marvelous Creations to Escorpiao

**Background:** Original plan was to acquire Marvelous Creations LDA from Bar and Oded. Oded's divorce proceedings blocked the share transfer (Oded's share is tied up in the divorce). Tania proposed buying Escorpiao LDA from Andre instead.

**Transaction structure (Escorpiao):**
- Perfil share: 2,400 (acquired by Zodiaco Badalado)
- Tatica share: 100 (acquired by Realization)
- Capital increase: 4,900 (Realization) + 8,100 (Zodiaco Badalado)
- Post-transaction: Realization 33% / Zodiaco 67% with 15,000 social capital
- Bank: Escorpiao IBAN PT50003600629910015892258
- Signing: At Tania's office (Andre, Eldad, Asaf present)

**All KB documents must be updated from "Marvelous Creations" to "Escorpiao LDA".**

---

## Recommended Governance Mechanism

For a ~2.6M residential development SPV with one cash-investor LP and one sweat-equity GP:

### Tiered Decision Matrix

| Threshold | Approval | Timeline |
|-----------|----------|----------|
| Operational (<5,000) | GP (Asaf) unilateral | Same day, reported monthly |
| Significant (5,000-15,000) | GP proposes, LP has 48h right of refusal | 48 hours |
| Strategic (>15,000 or >5% budget variance) | Joint written approval (GP + LP) | 5 business days |
| Fundamental (exit, new debt/equity, dissolution, land sale) | Unanimous consent | As needed |

### Additional Safeguards
- Dual-signature for banking above 10,000
- Monthly financial reports (Roy prepares, Meirav sends)
- Key-person clause: If Asaf cannot continue, LP appoints replacement or triggers orderly dissolution
- Deadlock resolution: Independent mediator if no agreement within 30 days
- Tag-along / drag-along: Standard mutual protections on any buyout offers

---

## Key Business Model Figures (Source of Truth)

| Metric | Value |
|--------|-------|
| Units | 11 (A through K) |
| Total sellable area | 578.42 sqm |
| Gross building area | 651.7 sqm |
| Base price | 4,200/sqm |
| Total revenue | 2,646,474 |
| Land cost | 175,000 |
| Construction cost | 1,280,000 (1,450/sqm) |
| Soft costs | 614,000 |
| Financing costs | 64,000 |
| Total budget | 2,150,000 (approx) |
| Net profit (after tax) | 391,643 |
| Bank loan | ~770,000 (60% LTC, 5% interest, 15 months) |
| Project duration | 21 months |
| Round 1 equity | 265,000 (Eldad 250K + Asaf 15K) |
| Round 1 pref return | 10% |
| Round 1 multiplier | 1.45x |
| Round 1 IRR | 21.6% annual |
| GP Promote | 30% of profit after capital return + preferred |
| LP Upside | 70% of profit after capital return + preferred |
| Developer sweat equity | ~46,000 (1% of capital stack) |

---

## Actions Required

| # | Action | Owner | Deadline |
|---|--------|-------|----------|
| 1 | Request Tania to draft pacto parassocial | Asaf | Before or at signing |
| 2 | Confirm dual-signature terms with Tania | Asaf | At signing meeting |
| 3 | Share cross-analysis with Eldad | Asaf | Before signing |
| 4 | Update business model: Round 1 pref 12% to 10% | Asaf | This week |
| 5 | Update investment memorandum with correct figures | Asaf | After signing |
| 6 | Update Arena KB (all files) | RealizeOS | Today |
