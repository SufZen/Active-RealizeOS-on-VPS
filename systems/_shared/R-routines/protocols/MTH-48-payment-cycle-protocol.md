# MTH-48 — Payment Cycle Protocol

> Shared Protocol | Used by: MC (ENT-05) | Agents: Finance Controller, Project Director

---

## Purpose

Governs the end-to-end payment process from invoice receipt to bank transfer. Ensures budget compliance, proper authorization at the correct governance tier, and full audit trail. Designed for SPV structures with multi-party governance.

## When to Use

- Processing any vendor or contractor invoice
- Approving any payment or expense
- Budget allocation or reallocation decisions
- Any disbursement of project funds

## The Payment Cycle

### Step 1: Invoice Receipt & Registration

**Actor:** Finance Controller

When an invoice arrives:
1. Register the invoice (vendor, amount, description, date, reference number)
2. Categorize by budget line (construction, professional fees, licensing, FF&E, etc.)
3. Verify the vendor is an approved supplier
4. Check for duplicate invoices (same vendor + same amount + similar date)

**Output:** Registered invoice with budget category assignment.

### Step 2: Budget Verification

**Actor:** Finance Controller

Check the invoice against the approved budget:

| Check | Pass | Fail |
|-------|------|------|
| Budget line has sufficient remaining allocation | Amount fits within budget line | Insufficient budget — flag for reallocation |
| Cumulative spend is within plan | Total category spend within variance threshold | Variance threshold exceeded — escalate |
| Invoice matches contracted rate/scope | Aligned with contract or SOW | Discrepancy — hold and clarify with vendor |

**Variance threshold:** If this payment pushes any budget category beyond the entity's variance threshold, the Finance Controller must flag it BEFORE proceeding to approval.

### Step 3: Technical Verification (If Applicable)

**Actor:** Project Director

For construction, renovation, or technical services:
1. Confirm the work described in the invoice was actually completed
2. Verify quality meets specifications
3. Check against project timeline and milestone schedule
4. For staged payments: confirm the milestone triggering this payment is achieved

**For fiscalizacao (inspection/supervision) invoices:**
- Cross-reference against inspection reports
- Verify sign-off from the designated supervision entity

**Output:** Technical approval or hold with specific issues.

### Step 4: Governance Tier Authorization

**Actor:** Varies by amount (see governance tiers below)

The payment must be authorized by the appropriate governance tier:

| Amount Range | Authorizer | Process |
|-------------|-----------|---------|
| Under internal GP threshold | GP representative (Project Director or Finance Controller) | Single approval |
| Between internal and joint GP threshold | Joint GP decision (all GP partners) | Written confirmation from all GP partners |
| Above LP approval threshold | LP approval required | Formal request with context, LP written approval |

**Authorization requirements:**
- Written confirmation (email, message, or signed document)
- Context: what the payment is for, budget status, any flags
- No verbal-only approvals for amounts above internal threshold

### Step 5: Payment Execution

**Actor:** Finance Controller

Once authorized:
1. Schedule the bank transfer (via designated bank account)
2. Record the payment details (date, amount, vendor, reference, authorizer)
3. Update the master financial tracker
4. File the invoice and authorization records

**Payment timing:**
- Standard: within 30 days of invoice date (unless contract specifies otherwise)
- Urgent: within 7 days (requires explicit justification)
- Advance payments: only with contractual basis and GP+LP approval

### Step 6: Reconciliation & Audit Trail

**Actor:** Finance Controller

After payment:
1. Reconcile against bank statement
2. Update budget tracker with actual payment
3. Recalculate remaining budget and variance
4. If variance threshold is now exceeded: flag in next MTH-47 investor report
5. File complete audit trail: invoice > verification > authorization > payment proof

---

## Governance Tiers

### MC / Arena Habitat (ENT-05)
```yaml
internal_gp_threshold: 5000  # EUR — GP can approve unilaterally
joint_gp_threshold: 10000    # EUR — requires all GP partners
lp_approval_threshold: 10000 # EUR — requires LP written approval
variance_threshold: 2.5      # % — exceeding triggers LP notification
bank: "NovoBanco"
gp_partners:
  - "Asaf (Realization) — Project Director"
  - "Roy — Finance Controller"
  - "Meirav — Capital & Sales"
lp: "Zodiaco (Eldad) — 67%"
fiscalizacao: "Designated inspection entity"
```

## Exception Handling

### Budget Overrun
If a payment would cause a budget category to exceed its allocation:
1. Finance Controller flags the overrun with specific numbers
2. Identify source of reallocation (which category has surplus)
3. Reallocation below LP threshold: GP approves the budget adjustment
4. Reallocation above LP threshold: LP approval required before payment
5. Document the reallocation in M-memory/decisions.md

### Disputed Invoice
If the invoice amount or scope is disputed:
1. Hold payment — do not process
2. Finance Controller or Project Director contacts vendor
3. Negotiate resolution (adjusted amount, scope clarification, credit note)
4. Once resolved, restart from Step 2 with corrected invoice
5. Log the dispute and resolution

### Emergency Payment
For genuinely urgent payments (safety, legal compliance, regulatory deadline):
1. GP lead authorizes with written justification
2. Payment proceeds immediately
3. Full documentation completed within 48 hours
4. LP notified in next reporting cycle (or immediately if above threshold)

---

## Quality Standards

- Every payment has a complete audit trail (invoice > verification > authorization > proof)
- No payment is processed without the correct governance tier approval
- Budget tracker is updated within 24 hours of every payment
- Variance is monitored continuously, not just at month-end
- All authorizations are written (no verbal-only approvals above internal threshold)
- Payment history feeds directly into MTH-47 investor reporting

---

> Status: active
> Last updated: 2026-02-10
