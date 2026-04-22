# Briefing Packet: 2026 Life Events & Capital Routing

> **Source of Truth**: This brief rolls up the data from the 5 consolidated deal dossiers (`deal-0`, `deal-a`, `deal-b`, `deal-c`, `deal-d`). It is a view, not a source. If facts change, the underlying dossier must be updated first.

## 1. Event Inventory

| Event | Description | Expected Amount | Dates (Earliest / Latest) | Counterparty | Constraint Type |
|-------|-------------|-----------------|---------------------------|--------------|-----------------|
| **0** | Prior-year mais-valias (Unpaid tax) | **OUTFLOW:** €5,000 - €11,548 | Deadline: Apr-Jun 2026 (IRS filing) | Finanças | **FIXED OBLIGATION** |
| **A** | Sell secondary property (50% share) | **INFLOW:** ~€43,146 (Net equity) | Est: July 2026 | Buyer (Negotiating) | Flexible (Optimization) |
| **B** | Buy HPP property (75% share buyout) | **OUTFLOW:** ~€37,000 - €40,000 (Down payment) | Est: Sep-Oct 2026 (After Event A) | Brother | Flexible (Optimization) |
| **C** | Dev-project investment (Escorpiao) | **OUTFLOW:** €13,500 | Deadline: This week (Apr 2026) | Escorpiao Diplomado LDA | Flexible Conduit (Company) |
| **D** | Eye-laser surgery | **OUTFLOW:** ~€500 (Net after brother pays €2k) | Est: May-Jun 2026 | IMO in Lisbon | Flexible |

---

## 2. Current Position Snapshot

> **Data Quality Status:** `PENDING RECONCILIATION`. The orchestrators must run Step 3 to reconcile this against `account-registry.md`.

| Asset / Pool | Amount (EUR) | Status |
|--------------|--------------|--------|
| Personal Cash | `TBD` | Needs bank statements |
| Company Cash (Realization LDA) | `TBD` | Needs bank statements |
| Liquid Securities | `TBD` | Needs statement |
| Illiquid Sleeves | `TBD` | |
| Reserve Floor | `TBD` | Needs policy check |

**Committed but not yet paid:**
- Event 0 Mais-valias tax (~€11.5K max)
- Event C Investment (€13.5K due this week)
- Event D Surgery (€500 net)

---

## 3. Portugal Tax Context

- **Residency Status:** Portugal tax resident.
- **NHR / IFICI Status:** `TBD` (Need to verify).
- **Last Year's IRS (2025):** Must file Anexo G for the Oct 2025 property sale (Event 0). The sale generated ~€71.4K in gain.
- **Company's IRC (2026):** You are the sole owner of Realization Unipessoal LDA. Event C's €13.5K investment will flow through here via a personal shareholder loan.
- **Open Finanças Matters:** The upcoming Modelo 3 filing for Event 0.
- **Critical Interaction:** Event 0's tax bill is directly reduced by the amount of cash reinvested into Event B (up to ~€108K). Maximizing the down payment on Event B minimizes Event 0's tax.

---

## 4. Mandate & Goals

> Drawn from `investment-policy.md`.

1. **Minimize Tax Leakage:** Leverage the Art. 10 CIRS reinvestment exemption by routing maximum viable capital from Event 0 into Event B. Use corporate conduit for Event C to optimize future dividend extraction.
2. **Protect Liquidity:** Ensure the personal reserve floor is not breached during the timing gap between Event 0's tax payment and Event A's inflow.
3. **Sequence Risk:** Ensure Event A closes and the mortgage is cleared *before* Event B's mortgage application to secure the ~80% financing.

---

## 5. Hard Constraints

- **Reserve Floor:** `TBD`
- **Maximum Illiquid Concentration:** `TBD`
- **Authority Mode:** `paper_execute` (Agents will only propose trades; you execute).
- **Drop-Dead Legal Dates:**
  - Event 0 IRS Filing: ~June 2026.
  - Event 0 Reinvestment Window Closes: October 2028 (36 months post-sale).

---

## 6. Open Questions

To be answered by the user before Strategy Pass (Step 4) begins:
1. **Balances:** What are the current cash balances in your Personal account and the Company account?
2. **NHR/IFICI:** Do you have NHR or IFICI status active for 2025/2026?
3. **Reserve Floor:** What is the minimum cash balance you require across your accounts at all times?
