# Snowhouse Finance Skill

Parse Icelandic bank statements (Arion Bank xlsx), translate to English, convert ISK→USD, categorize, and insert into Google Sheets.

## Google Sheet
- **ID:** `1wHAon2Q-q-47uCBq0N-QVThktq1j6pn6UugwAwhGUY8`
- **Tab:** `IS160370266501246501212600`
- **Columns (A-T):** Date, Amount ISK, Balance ISK, Amount USD, Balance USD, Description, Receipt No., Reference, Type (EN), Category (BOB), Transaction Key, Interest Day, Text Key, Payment Bank, Batch No., Interest Date, Recipient/Payer Name, Number, Recipient/Payer ID, Unique Key
- **Summary tab:** `Category Summary` (monthly totals)

## Exchange Rate
- **Rate:** 0.00807 ISK→USD (closing rate for the month)
- Store rate in sheet metadata as paper trail

## Prerequisites
- `gog` CLI authenticated (`lucasmpramos@gmail.com` — NOT snowhouse account)
- `openpyxl` installed (`pip3 install --break-system-packages openpyxl`)
- Python 3.12+

## Workflow (follow this order EXACTLY)

### Step 1: Parse xlsx
```bash
python3 ~/.openclaw/skills/snowhouse-finance/scripts/parse_bank_statement.py <file.xlsx> --rate 0.00807
```
Output: `<file>_parsed.json` (array of 20-element arrays matching sheet columns)

### Step 2: Categorize
```bash
python3 ~/.openclaw/skills/snowhouse-finance/scripts/categorize.py <file>_parsed.json
```
Reads `references/categories.md` for mapping. Uncategorized items get flagged for review.

### Step 3: Insert (with dedup + validation)
```bash
python3 ~/.openclaw/skills/snowhouse-finance/scripts/insert_to_sheet.py <file>_parsed_categorized.json
```
**This script:**
1. Validates all USD conversions before touching the sheet
2. Reads ENTIRE current sheet
3. Deduplicates by Unique Key (col T)
4. Prepends new rows
5. Writes ENTIRE sheet back (never partial!)
6. Verifies insertion by reading back

### Step 4: Update Category Summary
```bash
python3 ~/.openclaw/skills/snowhouse-finance/scripts/update_summary.py
```

### Step 5: Fix USD (if needed)
```bash
python3 ~/.openclaw/skills/snowhouse-finance/scripts/fix_usd.py [--dry-run]
```
Recalculates ALL Amount USD and Balance USD columns from ISK values.

## ⚠️ CRITICAL RULES (learned from Apr 15 incident)

1. **NEVER use `gog sheets update` on a partial range** — it OVERWRITES existing rows instead of inserting. Always read ALL rows, modify in memory, write ALL rows back.

2. **NEVER trust sheet keys after a partial write** — keys get shifted/misaligned. Always match by Unique Key from the xlsx source.

3. **ALWAYS validate USD amounts before insertion** — a $22k debit card charge is always wrong. The `insert_to_sheet.py` script will abort if validation fails.

4. **NEVER insert rows manually with `gog sheets update`** — use the script only. Manual = corruption.

5. **Unique Key column (T) is the dedup key** — xlsx column 17 (0-indexed). Not column 18.

6. **gog account is `lucasmpramos@gmail.com`** — NOT `lucasm@snowhouse.studio`. The snowhouse account doesn't have `gog auth export`.

## Category Reference
See `references/categories.md` for full mapping of Icelandic vendors → English categories.

## Common Icelandic Terms
- **Lykill fjármögnun** = Loan Payment (leasing)
- **CI000...** = Incoming transfer via online banking
- **Útvextir** = Overdraft interest
- **Færslugjöld** = Bank fee
- **Símgreiðsla** = Wire transfer
- **Debitkortafærsla** = Debit card
- **Reikningur** = Invoice
- **Payday ehf.** = Payroll service provider
- **Arion banki hf.** = Bank fee/transfer (large outgoing = Deel payment)
