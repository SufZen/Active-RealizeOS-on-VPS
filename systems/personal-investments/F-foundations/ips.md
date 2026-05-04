---
type: foundation
scope: personal-investments
purpose: Investment Policy Statement — the constitutional document governing all investment-system decisions
status: TEMPLATE — to be filled in by Asaf during scheduled session Tue May 5 2026 09:00-11:00 Lisbon
critical: This document overrides every other instruction. Risk Controller checks every action against it.
last_updated: 2026-05-04 (template skeleton; awaiting Asaf's numbers)
---

# Personal Investment Policy Statement (IPS)

**Owner:** Asaf Eyzenkot
**Effective date:** _[to be set when filled in]_
**Last review:** _[date]_
**Next scheduled review:** _[quarterly]_

## 1. Purpose & Philosophy

This document governs the management of Asaf Eyzenkot's personal investment portfolio. It is also the constitution that the Realization Investment Intelligence System (CIO, Risk Controller, Execution Controller, and Researcher agents) must read before every decision and check compliance against for every action.

### Investment philosophy
_[Asaf to fill in 3-5 sentences capturing personal worldview. Suggested anchors:]_
- Long-term wealth preservation with selective growth exposure, anchored to real assets where possible
- Diversification across asset classes, geographies, and currencies — given international lifestyle (Setúbal/Milan/Israel)
- Bias toward businesses understood first-hand (AI, RE, tech)
- Selective concentration where conviction is high; broad indexing as default
- Capital preservation > capital appreciation in any single quarter

### Time horizon
- Long-term portfolio: 10+ years
- Tactical sleeve: 6–24 months
- Cash reserve: liquid, 6-12 months operating expenses

## 2. Mandate (the hard targets)

| Metric | Target | Hard Limit |
|---|---|---|
| Real return target | _CPI + ___%_ (suggest 4%) | — |
| Volatility band | _____% – ____% annualized_ (suggest 8-14%) | not exceeding 18% |
| Maximum drawdown | _____%_ (suggest 20%) | hard stop at 25% — pause and review |
| Tracking error vs benchmark | _____%_ (suggest 6%) | — |
| Cash floor | ____ months of personal expenses (suggest 6) | never below 3 months |

**Benchmark:** _[choose: 60/40 global, MSCI World, custom blend]_

## 3. Asset Universe

### Liquid public market assets (this is what the system actively manages)

| Asset class | Target weight | Drift band |
|---|---|---|
| Equity | __% | ±__% |
| Fixed income | __% | ±__% |
| Cash & equivalents | __% | ±__% |
| Commodities | __% | ±__% |
| Crypto (BTC/ETH only, no leverage) | __% | ±__% |
| Tactical / opportunistic (requires explicit thesis) | __% | ±__% |
| **Total** | **100%** | — |

### Illiquid / private holdings (tracked but not managed by agents)
- Realization GP positions (Arena SPV via Realization Unipessoal LDA)
- MioLiving partnership economics (when realized)
- RealizeOS revenue stream (treated as ongoing income)
- Setúbal apartment (real estate, owner-occupied + AL income)
- _[Other]_

These appear in the ledger for total wealth view but are excluded from rebalancing logic.

## 4. Position Limits (hard rules — Risk Controller checks daily)

### Concentration
- No single equity position > __% of liquid portfolio (suggest: 8%)
- No single fund position > __% of liquid portfolio (suggest: 25%)
- Top 5 positions combined ≤ __% (suggest: 40%)

### Sector
- No single sector > __% of equity sleeve (suggest: 35%)
- Tech sector cap: __% of equity (suggest: 30% — given career exposure)

### Geography
- US exposure: __% min, __% max (suggest: 40-65%)
- Europe exposure: __% min, __% max (suggest: 15-35%)
- Israel exposure: __% min, __% max (suggest: 5-20%)
- Emerging markets: __% min, __% max (suggest: 0-15%)

### Currency
- USD: __% min, __% max
- EUR: __% min, __% max
- ILS: __% min, __% max
- Other: max __%

### Single-trade size
- No single trade > __% of liquid portfolio (suggest: 5%)

## 5. Forbidden Zones (never, regardless of opportunity)

- ❌ Leverage on crypto
- ❌ Margin on equities beyond __% of portfolio (suggest: 0%)
- ❌ Naked options
- ❌ Single-name concentration > 15% (Risk Controller hard-rejects)
- ❌ Investments without a written 2-paragraph thesis
- ❌ Trades during defined no-trade windows: _[fill in — e.g., 24h before/after major personal events, while traveling internationally]_
- ❌ Investments in personal exclusion list: _[fill in if any]_

## 6. Approval Thresholds (HITL gates)

| Trade size (% of liquid portfolio) | Approval required |
|---|---|
| < 0.5% | Auto (paused initially; all trades approval-gated in v1) |
| 0.5% – 2% | Telegram approval, single tap |
| 2% – 5% | Telegram approval with rationale required |
| > 5% | Telegram approval + 24h cooling-off period |
| > 10% | Not allowed — must split |

**During paper-trade phase:** all "executions" are paper, but approval flow is practiced for habit-building.

## 7. Rebalancing Rules

### Frequency
- **Calendar:** Quarterly review on the first weekday of Jan/Apr/Jul/Oct
- **Drift-triggered:** Any asset class drifts more than ±__% from target → rebalance proposal (suggest: ±5%)
- **Opportunistic:** CIO can propose rebalance any time with thesis; subject to approval gate

### Tax sensitivity
- Prefer rebalancing within tax-advantaged accounts when available
- Avoid realizing gains on positions held < 1 year unless thesis materially changed
- _[Asaf's tax residency considerations: PT NHR status, Israeli citizenship, international income]_

### Cost discipline
- Don't trade if expected post-tax benefit < 0.5% of trade value
- Bundle rebalances to minimize commission

## 8. Watchlist (active monitoring — Risk Controller alerts on movement)

| Symbol | Type | Reason watching | Trigger to act |
|---|---|---|---|
| _[fill in]_ | _[Equity/ETF/etc]_ | _[Why on watchlist]_ | _[Price/event trigger]_ |

## 9. Agent Boundaries (locked, do not edit per IPS update)

What agents CAN do:
- ✓ Read positions, balances, market data
- ✓ Generate rebalance proposals
- ✓ Generate research memos on watchlist names
- ✓ Flag IPS breaches in real-time
- ✓ Run scenario analyses

What agents CANNOT do:
- ✗ Execute any trade without explicit Telegram approval (real-money phase only after promotion gate)
- ✗ Modify this IPS document
- ✗ Use trading credentials (read-only API only in v1)

## 10. Reporting Cadence

| Frequency | What |
|---|---|
| Daily (silent unless breach) | Risk Controller checks all rules |
| Weekly (Mondays) | CIO portfolio review + rebalance proposals |
| Monthly (1st of month) | Performance attribution + Researcher meta-analysis |
| Quarterly | IPS review session + drawdown discussion if drew down >10% |
| Annual (early January) | Full IPS rewrite if needed + tax-loss harvesting + life-stage adjustments |

## Sign-off

This IPS is the constitution. Every agent reads it. Every action is checked against it. It overrides every other instruction in the system — no clever prompt, no urgent market event, no "exception just this once" beats the IPS.

If the IPS is wrong, change the IPS *first*, then act. Never act outside it.

**Asaf:** _[signature placeholder — date when finalized]_
