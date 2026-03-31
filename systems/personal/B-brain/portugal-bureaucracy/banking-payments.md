# Banking & International Payments

## What This Is

Managing banking across multiple entities (personal, Realization company, HomeAid company) and making international payments to partners in Israel and Italy requires understanding Portuguese banking infrastructure, SEPA/SWIFT conventions, and lower-cost alternatives. This guide covers account management, domestic payment systems, and international transfer options.

## When You Need This

- Opening or managing separate accounts for personal finances, Realization, and HomeAid
- Paying Israeli suppliers or receiving payments from Israel (outside SEPA)
- Paying Italian partners or receiving payments from Italy (within SEPA)
- Setting up Multibanco references for rental payments or service fees
- Using MB Way for domestic payments
- Onboarding a new employee at HomeAid (salary account setup)
- Making large transfers for property purchases

## Required Documents

### For Personal Account
- Cartão de Cidadão (valid)
- NIF
- Proof of address (comprovativo de morada — utility bill, bank statement, rental contract)
- Tax statement or proof of income (for higher-tier accounts)

### For Company Account (Realization or HomeAid)
- Certidão de Matrícula (company registration certificate from IRN — see irn-registo.md)
- NIPC (company tax number)
- Estatutos da empresa (company articles of association)
- Ata de nomeação dos gerentes (minutes appointing directors/managers)
- NIFs and Cartões de Cidadão of all gerentes/administradores with signing authority
- Proof of company address (registered office documentation)
- Most recent accounts (IES annual declaration) for existing companies

## Step-by-Step Process

### Managing Multiple Accounts (Personal vs Realization vs HomeAid)

**Best practice — keep all three strictly separate:**
- Personal account: day-to-day expenses, personal salary/drawings from companies, property income
- Realization account: all Realization consultancy income and expenses
- HomeAid account: employee salaries, client invoices, supplier payments, SS contributions

**Practical tips:**
- Consider keeping all three at the same bank (Caixa Geral de Depósitos, Millennium BCP, Novo Banco, or Santander are the main options) — this simplifies internal transfers and means one banking relationship
- Set up multi-entity online banking if your bank supports it (most Portuguese banks do)
- Alternatively, Revolut Business supports multiple business accounts with sub-wallets and is useful for international operations

### International Wire Transfers — Italy (SEPA)

Italy is within the SEPA (Single Euro Payments Area). Transfers to Italian bank accounts should use SEPA Credit Transfer:
- Use IBAN (Italian IBANs begin with IT)
- BIC/SWIFT not required for SEPA (but have it on file)
- Cost: €0-5 depending on your bank; most online banking platforms offer free SEPA transfers
- Timeline: same day if submitted before your bank's cut-off (typically 15h-17h)
- For recurring payments, set up a standing order (ordem permanente)

### International Wire Transfers — Israel (SWIFT / outside SEPA)

Israel is outside SEPA. Payments to Israeli accounts require SWIFT transfers:
- Obtain from your Israeli counterpart: IBAN (Israeli IBANs begin with IL) + SWIFT/BIC code of their bank
- Use your bank's "Transferência Internacional" or "Pagamento ao Exterior" option in online banking
- You will need to declare the purpose of payment (purpose code) — typical codes: "services rendered", "consulting fee", "trade goods"
- Timeline: 1-3 business days (sometimes up to 5 for first-time recipients)
- Cost via traditional Portuguese bank: €15-35 per transfer + exchange rate margin (if paying in NIS rather than EUR)
- For larger amounts (€10,000+), your bank may contact you for AML verification — have invoices ready

**Preferred alternative for Israel — Wise (formerly TransferWise):**
1. Create a Wise Business account at wise.com
2. Verify identity with Cartão de Cidadão + company documents
3. Send EUR from your Portuguese IBAN to Wise
4. Wise converts to NIS (or USD/EUR if your Israeli partner prefers) at mid-market rate
5. Fee: approximately 0.4-1.0% of transfer amount — significantly cheaper than bank SWIFT
6. Timeline: 1-2 business days to Israeli bank
7. Wise also allows you to hold a EUR balance and receive EUR payments from Italian clients

### Wise Setup (Recommended for International Payments)

1. Register at wise.com/business
2. Verify with: NIF, Cartão de Cidadão, company certidão de matrícula, proof of address
3. Connect your Portuguese IBAN as the funding source
4. For receiving: Wise gives you a EUR IBAN (Belgian or Lithuanian routing) — useful for receiving payments from Italian clients without exchange fees
5. For Israeli NIS payments: Wise gives competitive rates; confirm with your Israeli partner what they prefer (USD, EUR, or NIS)

### Multibanco References (Referências Multibanco)

The Multibanco system allows payments via a 3-field reference: Entity (Entidade), Reference (Referência), Amount (Valor).
- Used for: utility bills, government fees, online purchases, rental payments
- To pay: any ATM > "Pagamentos e Transferências" > "Serviços"; or via online banking > "Pagamentos Multibanco"
- If you want to receive Multibanco payments (e.g., for HomeAid services): you need a Multibanco payment integration — ask your bank about "integração SIBS" or use a payment processor like Eupago, IFTHENPAY, or Stripe (which supports Multibanco)

### MB Way Setup and Limits

MB Way is Portugal's instant mobile payment system, linked to your debit card:
1. Download "MB WAY" app
2. Associate your Portuguese bank debit card (most banks supported)
3. Confirm via SMS to Portuguese mobile number
4. Use for: splitting payments, instant transfers between MB Way users, paying in stores, paying online

**Limits (standard — varies by bank):**
- Single transfer: €150 (can be raised to €500 with bank confirmation)
- Daily limit: €300-1,000 depending on bank
- Not suitable for large business payments — use SEPA/SWIFT for those

**Note:** MB Way requires a Portuguese mobile number (+351). Your Israeli or Italian partners cannot use MB Way.

### Opening a Company Account for HomeAid or Realization

1. Contact your chosen bank's business banking (banca empresas) department
2. Book an appointment — bring all documents listed in Required Documents above
3. Banks typically also require:
   - Livro de registo de sócios (shareholder register) or equivalent
   - Declaration of beneficial ownership (beneficiário efetivo) — also registered on the Registo Central do Beneficiário Efetivo (RCBE) portal at rcbe.justica.gov.pt
4. RCBE registration is mandatory for all Portuguese companies — register at rcbe.justica.gov.pt with your Chave Móvel Digital; penalty for non-compliance is €1,000+
5. Account opening: typically 3-7 business days after all documents submitted
6. Online banking access granted upon account opening

## Key Contacts / Numbers / Websites

| Resource | Details |
|---|---|
| Wise (international transfers) | wise.com |
| RCBE (beneficial ownership registry) | rcbe.justica.gov.pt |
| SIBS (MB Way operator) | sibs.pt |
| Caixa Geral de Depósitos | cgd.pt |
| Millennium BCP | millenniumbcp.pt |
| Novo Banco | novobanco.pt |
| Santander Portugal | santander.pt |
| Banco de Portugal (regulator) | bportugal.pt |
| SEPA country list confirmation | europeanpaymentscouncil.eu |

## Common Mistakes to Avoid

- **Using personal account for HomeAid or Realization transactions** — this complicates accounting, triggers AT scrutiny, and is a red flag in audits
- **Not filing RCBE for your companies** — every Portuguese company must register its beneficiário efetivo annually; fines are significant and it's now required for opening bank accounts
- **Using bank SWIFT for recurring small Israel payments** — fees add up; switch to Wise for anything under €5,000
- **Not keeping SWIFT transfer documentation** — for payments to Israel especially, keep all invoices and purpose-of-payment records (AT and bank may ask for these)
- **MB Way for business payments** — MB Way is for personal use; using it for business income creates untraceable revenue (a tax risk)
- **Not having a valid company address in the NIPC** — if your company's registered address has changed and AT records are not updated, banks and counterparties may reject documentation
- **Forgetting to update signatory authority at the bank** — if company management changes (gerente added/removed), update the bank's records immediately with a certified ata and updated certidão de matrícula

## Estimated Timeline & Cost

| Task | Timeline | Cost |
|---|---|---|
| SEPA transfer to Italy | Same day (before cut-off) | €0-5 |
| SWIFT transfer to Israel (via bank) | 1-3 business days | €15-35 + FX margin |
| SWIFT transfer to Israel (via Wise) | 1-2 business days | ~0.5-1.0% of amount |
| MB Way setup | 15 minutes | Free |
| Company bank account opening | 3-7 business days | Free or small annual fee |
| Multibanco payment integration (for receiving) | 3-5 business days | Setup fee + per-transaction fee (varies by provider) |
| RCBE registration (annual) | 30 minutes online | Free |
