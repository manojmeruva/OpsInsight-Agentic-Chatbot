### DOMAIN LOGIC & CONTEXT
**Domain:** Finance — Accounts & Transactions
**Purpose:** Answer questions about banks, customer accounts, balances and the credit/debit transactions posted to those accounts.

**Data model (3 tables, one database):**
- One `bank` has many `account` rows; one `account` has many `transaction` rows.

TABLE: bank  — master list of partner banks
| Column     | Type         | Notes |
|------------|--------------|-------|
| bank_code  | VARCHAR(10)  | PRIMARY KEY. IFSC prefix, e.g. 'HDFC', 'ICIC', 'SBIN', 'UTIB', 'KKBK', 'CNRB', 'UBIN', 'AUBL', 'TMBL', 'RATN' |
| bank_name  | VARCHAR(150) | Canonical ALL-CAPS formal name, e.g. 'HDFC BANK LIMITED' |

Valid bank_code → bank_name values (the ONLY banks that exist — never invent another):
- HDFC → HDFC BANK LIMITED
- ICIC → ICICI BANK LIMITED
- SBIN → STATE BANK OF INDIA
- UTIB → AXIS BANK LIMITED
- KKBK → KOTAK MAHINDRA BANK LIMITED
- CNRB → CANARA BANK
- UBIN → UNION BANK OF INDIA
- AUBL → AU SMALL FINANCE BANK LIMITED
- TMBL → TAMILNAD MERCANTILE BANK LIMITED
- RATN → RBL BANK LIMITED

TABLE: account  — one row per account
| Column            | Type          | Notes |
|-------------------|---------------|-------|
| account_id        | VARCHAR(36)   | PRIMARY KEY (UUID) |
| entity_id         | VARCHAR(36)   | UUID of the customer/entity that owns the account. One entity may own several accounts |
| account_number    | VARCHAR(20)   | SENSITIVE. Never display raw — see masking rule |
| program_id        | INT           | Product/program the account belongs to (e.g. 4, 21, 46). Refer to it as "Program <id>"; names are not known |
| available_balance | DECIMAL(15,2) | Current balance in INR. Negative = overdrawn / drawn credit line |
| bank_code         | VARCHAR(10)   | FK → bank.bank_code |

TABLE: transaction  — one row per credit or debit
| Column                   | Type          | Notes |
|--------------------------|---------------|-------|
| transaction_id           | VARCHAR(36)   | PRIMARY KEY (UUID) |
| account_id               | VARCHAR(36)   | FK → account.account_id |
| transaction_date         | TIMESTAMP(6)  | 'YYYY-MM-DD HH:MM:SS.ffffff' |
| transaction_type         | ENUM          | ONLY 'credit' or 'debit' (lower case) |
| description              | VARCHAR(500)  | Free-text narration, e.g. 'NEFT  - ICIC0001241 - ... - SELECTION MOBILE', 'IMPS charges', 'Cheque Deposits' |
| transaction_amount       | DECIMAL(15,2) | Always positive; direction comes from transaction_type |
| transaction_reference_id | VARCHAR(64)   | PLAINTEXT reference / receipt number — directly searchable |
| utr_number               | VARCHAR(256)  | SENSITIVE + ENCRYPTED at rest. Not searchable with WHERE =, never display |

Joins:
- account.bank_code = bank.bank_code
- `transaction`.account_id = account.account_id

### MANDATORY SQL RULES
1. Table name quoting: `transaction` is a reserved word. ALWAYS write it with backticks: FROM `transaction` t. Use short aliases: b (bank), a (account), t (transaction).
2. Money:
   - Credits (inflow): t.transaction_type = 'credit'. Debits (outflow): t.transaction_type = 'debit'.
   - Net flow = SUM(CASE WHEN t.transaction_type = 'credit' THEN t.transaction_amount ELSE -t.transaction_amount END).
   - Round money to 2 decimals with ROUND(x, 2). All amounts are INR — label columns "(INR)" and prefix "₹" in text.
3. Balances come ONLY from account.available_balance. Do not recompute a balance from transactions unless the user explicitly asks for a running total.
   - "Overdrawn", "negative balance", "in debit" → a.available_balance < 0.
4. Banks: always resolve a bank via the bank table. Match user wording case-insensitively against bank_name or bank_code, e.g.
   WHERE UPPER(b.bank_name) LIKE '%HDFC%' OR b.bank_code = 'HDFC'. Common aliases: "Axis" → UTIB, "SBI" → SBIN, "Kotak" → KKBK, "RBL" → RATN, "AU" / "AU Small Finance" → AUBL, "Union Bank" → UBIN, "TMB" → TMBL.
   If the user names a bank that is not in the list above, say it is not available — never invent a bank.
5. Reference numbers:
   - A bare "reference number", "ref no", "receipt number", "txn ref" → search transaction_reference_id (plaintext): WHERE TRIM(t.transaction_reference_id) = '<value>'.
   - Only if the user explicitly says "UTR" may you look at utr_number. utr_number is encrypted, so it CANNOT be matched with WHERE = or LIKE. Return a text answer explaining that UTR values are encrypted and offer to search by the plaintext reference number; you may report whether a UTR is present (utr_number IS NOT NULL) but never its value.
6. Sensitive data masking:
   - NEVER select utr_number into an output column.
   - account_number may only be shown masked to the last 4 digits. Select it and mask it in Python before returning:
       df['Account No.'] = df['Account No.'].astype(str).str[-4:].radd('XXXXXX')
   - "account ending 1234" / "a/c 1234" → filter with the last-4 suffix: a.account_number LIKE '%1234'.
   - Do not display full account_id / entity_id / transaction_id UUIDs unless the user asks for an ID; if needed show the first 8 characters.
7. Payment rail / channel is derived from the description. Use this exact CASE expression when the user asks about NEFT, IMPS, UPI, RTGS, channels, modes or payment methods:
     CASE
       WHEN UPPER(t.description) LIKE '%CHARGE%' THEN 'Charges'
       WHEN UPPER(t.description) LIKE '%NEFT%' THEN 'NEFT'
       WHEN UPPER(t.description) LIKE '%IMPS%' THEN 'IMPS'
       WHEN UPPER(t.description) LIKE 'UPI%' THEN 'UPI'
       WHEN UPPER(t.description) LIKE '%RTGS%' OR UPPER(t.description) LIKE 'R/%' THEN 'RTGS'
       WHEN UPPER(t.description) LIKE 'FT%' THEN 'Fund Transfer'
       WHEN UPPER(t.description) LIKE '%CHEQUE%' OR UPPER(t.description) LIKE '%CHQ%' THEN 'Cheque'
       WHEN UPPER(t.description) LIKE '%BAJAJ FINANCE%' THEN 'Loan Disbursement'
       ELSE 'Other'
     END AS channel
8. Counterparties / merchants (e.g. "Selection Electronics", "Reliance Digital", "Bajaj Finance") appear only inside description. Match with UPPER(t.description) LIKE '%SELECTION%' style filters.
9. Time:
   - Use t.transaction_date for all time filters. Compute relative periods ("last month", "last 90 days", "this year") from the CURRENT DATETIME given to you and filter with a half-open range of literal dates: t.transaction_date >= '<start>' AND t.transaction_date < '<end>'.
   - If the user gives a month without a year, assume the most recent such month on or before the current date.
   - If the user gives no period at all, use all available data and say so in the text ("across all available history").
10. Programs: refer to program_id as "Program 21" etc. Group by a.program_id when asked "by program/product".
11. Customers / entities: "customer", "client", "entity" → account.entity_id. Count customers with COUNT(DISTINCT a.entity_id).
12. Counting: transactions → COUNT(t.transaction_id); accounts → COUNT(DISTINCT a.account_id).
13. Ordering & grouping: use column positions (GROUP BY 1 ORDER BY 2 DESC). For "top/highest/largest" use ORDER BY ... DESC LIMIT N (default N = 10).
14. Aliases: internal subquery aliases use snake_case without spaces; only the outermost SELECT uses friendly names with spaces in double quotes, e.g. "Total Debits (INR)".

### FEW-SHOT EXAMPLES (question → SQL)

Q: What is the total available balance by bank?
SQL:
SELECT b.bank_name AS "Bank",
       COUNT(DISTINCT a.account_id) AS "Accounts",
       ROUND(SUM(a.available_balance), 2) AS "Total Available Balance (INR)"
FROM account a
JOIN bank b ON b.bank_code = a.bank_code
GROUP BY 1
ORDER BY 3 DESC
LIMIT 200;

Q: Which accounts are overdrawn?
SQL:
SELECT b.bank_name AS "Bank",
       a.account_number AS "Account No.",
       a.program_id AS "Program",
       ROUND(a.available_balance, 2) AS "Available Balance (INR)"
FROM account a
JOIN bank b ON b.bank_code = a.bank_code
WHERE a.available_balance < 0
ORDER BY 4 ASC
LIMIT 200;
(Python must mask "Account No." to the last 4 digits.)

Q: Credits vs debits per month for the last 6 months (current date 2026-07-15)
SQL (use the month-bucket expression from the SQL DIALECT section):
SELECT <month bucket of t.transaction_date> AS "Month",
       ROUND(SUM(CASE WHEN t.transaction_type = 'credit' THEN t.transaction_amount ELSE 0 END), 2) AS "Credits (INR)",
       ROUND(SUM(CASE WHEN t.transaction_type = 'debit'  THEN t.transaction_amount ELSE 0 END), 2) AS "Debits (INR)"
FROM `transaction` t
WHERE t.transaction_date >= '2026-01-01' AND t.transaction_date < '2026-07-01'
GROUP BY 1
ORDER BY 1
LIMIT 200;

Q: Find transaction with reference number HDFCH01078329532
SQL:
SELECT t.transaction_date AS "Date",
       t.transaction_type AS "Type",
       ROUND(t.transaction_amount, 2) AS "Amount (INR)",
       t.description AS "Description",
       t.transaction_reference_id AS "Reference No.",
       b.bank_name AS "Bank",
       a.account_number AS "Account No."
FROM `transaction` t
JOIN account a ON a.account_id = t.account_id
JOIN bank b ON b.bank_code = a.bank_code
WHERE TRIM(t.transaction_reference_id) = 'HDFCH01078329532'
LIMIT 200;

Q: Net cash flow for account ending 9069 in June 2026
SQL:
SELECT ROUND(SUM(CASE WHEN t.transaction_type = 'credit' THEN t.transaction_amount ELSE -t.transaction_amount END), 2) AS "Net Cash Flow (INR)"
FROM `transaction` t
JOIN account a ON a.account_id = t.account_id
WHERE a.account_number LIKE '%9069'
  AND t.transaction_date >= '2026-06-01' AND t.transaction_date < '2026-07-01'
LIMIT 200;
