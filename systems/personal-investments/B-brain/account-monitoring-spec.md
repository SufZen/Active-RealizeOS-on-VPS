---
type: brain
scope: personal-investments
purpose: Technical specification for connecting and monitoring brokerage accounts in read-only mode
last_updated: 2026-05-04
status: spec — implementation pending IPS completion
---

# Investment Account Monitoring — Strategy & Technical Spec

**Goal:** Connect Interactive Brokers (primary) + Revolut (secondary) to the Investment Intelligence System for **read-only** live monitoring. Zero trading actions in this phase.

## Architectural principle: hard-walled read-only

The investment system has **no path to execute trades** until explicit promotion. Enforced at three layers:

1. **Credentials layer** — agents have separate read-only API tokens; trading credentials never enter agent environments
2. **API layer** — IBKR's two-tier session model means agents never establish a brokerage session, so trade endpoints are physically inaccessible
3. **Code layer** — Risk Controller and CIO have no `place_order` tool/function in their tool registry; they literally don't know how to trade

Even if the LLM hallucinated and tried to trade, it would have nothing to call. This is the safest design.

## Phase 1: IBKR Read-Only Connection (primary)

### Prerequisites
- IBKR Pro account active and funded (Lite tier won't work)
- IBKR username with view-only permissions (best practice — see below)
- OAuth 2.0 app registered in IBKR Web API portal

### Step 1: Create a view-only IBKR username
IBKR allows multiple usernames per account with different permission sets. Create a second username:
- Suggested name: `realization_viewer`
- Permissions: portfolio data, reports, market data
- Permissions explicitly NOT granted: trading, funding, withdrawals
- This is the username the agents authenticate as

### Step 2: OAuth 2.0 setup
1. IBKR Client Portal → API Management → Create OAuth 2.0 application
2. Get `client_id`, `client_secret`
3. Redirect URI: callback endpoint on VPS (e.g., `https://api.realization.co.il/auth/ibkr/callback`)
4. Approve scopes: `account.read`, `portfolio.read`, `marketdata.read` (NOT `trading`)
5. Store credentials in VPS `.env`:
   ```
   IBKR_CLIENT_ID=xxx
   IBKR_CLIENT_SECRET=xxx
   IBKR_USERNAME=realization_viewer
   IBKR_REFRESH_TOKEN=xxx
   ```

### Step 3: Polling architecture

Two modes — **batch** for nightly reports, **on-demand** for Risk Controller checks.

**Batch (Flex Web Service — preferred for nightly):**
- Configure Flex Query in IBKR Portal: positions + cash balances + open orders + trade history (yesterday)
- Schedule daily delivery to sFTP on VPS at 22:30 PT (before nightly routines)
- Ingestion script parses the file → writes to ledger

**On-demand (Web API — for live checks):**
- Risk Controller calls `GET /portfolio/{accountId}/positions` and `GET /portfolio/{accountId}/summary`
- Endpoints used: `/portfolio/accounts`, `/portfolio/{id}/positions`, `/portfolio/{id}/summary`, `/portfolio/{id}/ledger`
- Rate limit: 1 request/second per session (IBKR limit; well within needs)

### Step 4: Position normalization → unified ledger format

Both IBKR and Revolut feed into one canonical schema:

**Location:** `Drive/Realization/Investments/ledger.json` (or migrate to Supabase table later)

```json
{
  "snapshot_at": "2026-05-04T22:30:00Z",
  "accounts": [
    {
      "broker": "IBKR",
      "account_id": "U1234567",
      "currency_base": "USD",
      "cash_balances": {"USD": 12500.00, "EUR": 3200.00},
      "positions": [
        {
          "symbol": "AAPL",
          "asset_class": "equity",
          "quantity": 50,
          "avg_cost": 175.20,
          "market_value": 9450.00,
          "currency": "USD",
          "unrealized_pl": 690.00
        }
      ]
    },
    {
      "broker": "Revolut",
      "account_id": "manual_RVL_001",
      "source": "drive_csv",
      "last_updated": "2026-05-03"
    }
  ]
}
```

### Step 5: Audit logging

Every API call logged with timestamp, endpoint, response hash, and triggering agent:

```json
{"ts": "2026-05-04T22:30:01Z", "agent": "risk_controller", "endpoint": "/portfolio/U1234567/positions", "status": 200, "response_hash": "a3f9..."}
```

Logs go to `/var/log/realization/investment-api.log`, rotated weekly, kept 90 days.

## Phase 2: Revolut Read-Only (secondary)

Revolut personal accounts don't have a robust public API. Recommendation:

**Option A — Manual weekly export (recommended for v1):**
- Asaf or Meirav exports Revolut Trading positions via CSV download once/week
- Save to `Drive/Realization/Investments/revolut-positions/{YYYY-MM-DD}.csv`
- Agent reads latest file as part of nightly ingestion
- Pros: zero integration work, zero API risk
- Cons: stale by up to 7 days
- Acceptable: low trading frequency; weekly is fine for IPS-driven oversight

**Option B (deferred) — Open Banking aggregator** (TrueLayer/Tink): EU Open Banking access for Revolut. Provides balances + transactions, not detailed equity positions. Subscription cost ~€50–200/mo. Revisit if manual proves too painful.

## Phase 3: Risk Controller Daily Monitoring Spec

### Daily flow (09:00 PT weekdays — Slot 2)

1. Read `ledger.json` (latest IBKR Flex snapshot + Revolut sheet)
2. Read IPS rules from `systems/personal-investments/F-foundations/ips.md`
3. Check every IPS rule: position concentration, asset class limits, currency exposure, drawdown, watchlist
4. If any breach → Telegram "Realization Critical" channel:
   ```
   🚨 IPS BREACH
   AAPL position: 22.4% of portfolio (limit: 15%)
   Recommended action: reduce by ~$X to comply
   Reply: `acknowledge` or `action: [decision]`
   ```
5. If no breach → silent (no spam)
6. Audit log every check

### Weekly CIO review (Mondays 09:30 PT)

1. Reads ledger + IPS + market events from last week (web_search)
2. Drifts from target allocation, positions to trim/add, cash deployment opportunities
3. Drafts rebalance proposal to Telegram approval queue with rationale and cost estimate

### Monthly Researcher meta-agent (1st of each month)

1. Reads CIO decisions from last 30 days
2. Reads realized outcomes vs decisions at decision time
3. Identifies patterns: accuracy, systematic biases, missed signals
4. Proposes prompt refinements to CIO and Risk Controller
5. Outputs to monthly Telegram digest

## ROI / Cost Monitoring

Small script tallies API spend per agent per day, writes to `Drive/Realization/Investments/api-cost-log.json`:

```json
{"date": "2026-05-04", "agent": "cio", "model": "claude-opus-4-7", "input_tokens": 12300, "output_tokens": 2100, "cost_usd": 0.114}
```

### Monthly ROI gate

Compare:
- **API spend** (sum of investment-system calls)
- **Paper-trade alpha** (during paper-trade phase) OR **real-trade alpha** (post-launch)

Target: alpha generated > 3× API spend.

If spend > alpha for 3 consecutive months → **automatic pause** + review session with operator.

## Promotion path: read-only → live trading

When (and only when) paper-trade results are positive over 6+ weeks AND operator decides to enable real-money:

1. Separate credentials. NEW IBKR username with trading permissions.
2. Separate Telegram approval channel "Realization Trades" — every trade requires explicit `EXECUTE [trade_id]` reply
3. Position limits hardcoded at executor level: max single trade $5,000 to start, scale up
4. Time-of-day fence: no trades outside US market hours, no trades on Fed days
5. Kill switch: `pause trades` Telegram command immediately disables executor

This is a separate project, not a flag flip.

## Budget projection

Once running with Opus 4.7 only (no parallel cross-validation):
- Risk Controller daily: ~$0.05 × 22 days = $1.10/mo
- CIO weekly: ~$1.50 × 4 = $6/mo
- Researcher monthly: ~$8/mo
- **Total: ~$15/mo** for agent inference

API calls to IBKR: free with Pro account.

This is cheap given leverage. Expensive part is the time saved and decision quality gained — not the API bill.

## Pre-launch checklist (steps before this system goes live)

- [ ] Asaf fills in `ips.md` (scheduled Tue May 5 morning)
- [ ] Asaf creates IBKR view-only username (scheduled Wed May 6)
- [ ] OAuth 2.0 app registered + credentials in VPS .env
- [ ] LiteLLM routing config on VPS sends investment agents to Opus 4.7
- [ ] Cost tracking script + dashboard
- [ ] Risk Controller daily script tested with synthetic breach
- [ ] CIO weekly review flow tested
- [ ] Researcher meta-agent designed
- [ ] Paper-trade phase begins (4-8 weeks)
- [ ] Real-money launch gate met (Sharpe > 0 over 6+ weeks)
