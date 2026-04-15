# Snowhouse Finance Skill

Parse Icelandic bank statements (Arion Bank xlsx), translate to English, convert ISK→USD, categorize, insert into the transaction tracking sheet, and update the DRE (P&L) balance sheet.

## Google Sheets

### 1. Transaction Sheet (Source of Truth)
- **ID:** `1wHAon2Q-q-47uCBq0N-QVThktq1j6pn6UugwAwhGUY8`
- **Tab:** `IS160370266501246501212600`
- **Columns (A-T):** Date, Amount ISK, Balance ISK, Amount USD, Balance USD, Description, Receipt No., Reference, Type (EN), Category (BOB), Transaction Key, Interest Day, Text Key, Payment Bank, Batch No., Interest Date, Recipient/Payer Name, Number, Recipient/Payer ID, Unique Key
- **Summary tab:** `Category Summary` (monthly totals)
- **Account:** `lucasmpramos@gmail.com`

### 2. DRE Balance Sheet (P&L)
- **ID:** `112cV3ac8s1ex0tLKQhLheJwTIaCavoRDnmcCdEABoI4`
- **Tabs:** DRE, Income, Expenses, Categories
- **Account:** `lucasmpramos@gmail.com`

**DRE tab structure (row layout):**
```
Row 1:  SNOWHOUSE DRE 2026
Row 3:  Category | Jan | Feb | ... | Dec | YTD
Row 5:  📈 INCOME
Row 6:  Retainer
Row 7:  Project
Row 8:  Other Income
Row 9:  Total Income (=SUM of rows 6-8)
Row 11: 📉 EXPENSES
Row 12: Salaries & Contractors
Row 13: Revenue Share
Row 14: Software & Tools
Row 15: Marketing
Row 16: Office & Admin
Row 17: Taxes
Row 18: Bank Fees
Row 19: Thor Personal
Row 20: Other Expense
Row 21: Total Expenses (=SUM of rows 12-20)
Row 23: 💰 NET PROFIT (=Total Income - Total Expenses)
Row 25: 🏦 OPENING BALANCE (-$22,856.35)
```

**DRE formulas:** SUMIFS referencing Income/Expenses tabs. Example (Retainer, Jan):
```
=SUMIFS(Income!$C:$C, Income!$E:$E, "Retainer", Income!$A:$A, ">="&DATE(2026,1,1), Income!$A:$A, "<"&DATE(2026,2,1))
```
Columns B-M = Jan-Dec, Column N = YTD (SUM of B:M).

**Income tab:** Date | Client | Amount (USD) | Currency | Category | Notes
**Expenses tab:** Date | Payee | Amount (USD) | Currency | Category | Notes
**Categories tab:** Lists all 13 categories for data validation dropdowns.

**Category dropdown** on col E of Income/Expenses tabs, sourced from Categories tab.

## Category Mapping (Transaction Sheet → DRE)

The transaction sheet categories need to map to DRE categories:

| Transaction Sheet Category | DRE Category | Tab |
|---|---|---|
| Transfer / CI000... | Other Income | Income |
| PAYPAL / incoming | Other Income | Income |
| (any positive amount) | Other Income | Income |
| Salaries & Contractors | Salaries & Contractors | Expenses |
| Payroll Service | Salaries & Contractors | Expenses |
| Software / Software — Design | Software & Tools | Expenses |
| Bank Fee | Bank Fees | Expenses |
| Loan Payment / Leasing | Bank Fees | Expenses |
| Overdraft interest | Bank Fees | Expenses |
| Insurance | Office & Admin | Expenses |
| Pension Fund | Office & Admin | Expenses |
| Thor Personal | Thor Personal | Expenses |
| Marketing | Marketing | Expenses |
| Taxes | Taxes | Expenses |
| Uncategorized | Other Expense | Expenses |
| Entertainment | Other Expense | Expenses |

## Exchange Rate
- **Rate:** 0.00807 ISK→USD (closing rate for the month)
- Store rate in sheet as paper trail

## Prerequisites
- `gog` CLI authenticated (`lucasmpramos@gmail.com`)
- `openpyxl` installed (`pip3 install --break-system-packages openpyxl`)
- Python 3.12+

## Workflow

### Step 1: Parse xlsx
```bash
python3 ~/.openclaw/skills/snowhouse-finance/scripts/parse_bank_statement.py <file.xlsx> --rate 0.00807
```

### Step 2: Categorize
```bash
python3 ~/.openclaw/skills/snowhouse-finance/scripts/categorize.py <file>_parsed.json
```

### Step 3: Insert into Transaction Sheet
```bash
python3 ~/.openclaw/skills/snowhouse-finance/scripts/insert_to_sheet.py <file>_parsed_categorized.json
```

### Step 4: Update DRE Balance Sheet
```bash
python3 ~/.openclaw/skills/snowhouse-finance/scripts/update_dre.py
```
This script:
1. Reads all new transactions from the Transaction Sheet
2. Maps Transaction categories → DRE categories
3. For each transaction: positive amounts → Income tab, negative → Expenses tab (absolute value)
4. Inserts into DRE Income/Expenses tabs
5. SUMIFS formulas auto-update the DRE summary

### Step 5: Update Category Summary (Transaction Sheet)
```bash
python3 ~/.openclaw/skills/snowhouse-finance/scripts/update_summary.py
```

### Step 6: Fix USD (if needed)
```bash
python3 ~/.openclaw/skills/snowhouse-finance/scripts/fix_usd.py [--dry-run]
```

## ⚠️ CRITICAL RULES

1. **NEVER use `gog sheets update` on a partial range** — OVERWRITES instead of inserts. Always read ALL rows, modify, write ALL back.
2. **NEVER trust sheet keys after a partial write** — keys get shifted. Always match by Unique Key from xlsx.
3. **ALWAYS validate USD amounts before insertion** — the insert script aborts if amounts look wrong.
4. **NEVER insert rows manually** — use the scripts only. Manual = corruption.
5. **Unique Key column (T)** — xlsx column 17 (0-indexed).
6. **gog account is `lucasmpramos@gmail.com`** — NOT snowhouse account.
7. **DRE formulas use SUMIFS** — `gog sheets update` mangles formulas. Use Sheets API batchUpdate via Node script for any formula work.
8. **DRE amounts are always positive** — Income tabs store positive amounts, Expenses tabs store positive amounts (absolute value). The SUMIFS just sums by category.
9. **Opening balance:** -$22,856.35 (set by Luke, don't change).
10. **Revenue Share** is an EXPENSE category (how Fernando & Darlan are paid), NOT income.
11. **Thor Personal** = yellow-highlighted items from bank statement (personal expenses).
12. **Preserve formatting** — DRE has colors, bold headers, emoji. Don't overwrite.

## Common Icelandic Terms
- **Lykill fjármögnun** = Loan Payment (leasing) → maps to Bank Fees in DRE
- **CI000...** = Incoming transfer → maps to Other Income in DRE
- **Útvextir** = Overdraft interest → Bank Fees
- **Færslugjöld** = Bank fee → Bank Fees
- **Símgreiðsla** = Wire transfer
- **Debitkortafærsla** = Debit card
- **Payday ehf.** = Payroll service → Salaries & Contractors
- **Arion banki hf.** = Bank transfer (large outgoing = Deel payment) → Salaries & Contractors
- **TM tryggingar** / **Sjóvá-Almennar** = Insurance → Office & Admin
- **Gildi lífeyrissjóður** = Pension fund → Office & Admin
- **DONE ehf.** = Uncategorized (ask Luke)
