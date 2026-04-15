#!/usr/bin/env python3
"""Update the Snowhouse DRE 2026 balance sheet from the Transaction Sheet.

Reads categorized transactions from the Icelandic bank statement sheet,
maps categories to DRE categories, and inserts into Income/Expenses tabs.
DRE SUMIFS formulas auto-update the summary.

CRITICAL: This script reads all existing DRE rows, deduplicates by date+payee+amount,
and writes ALL rows back (never partial overwrite).

Usage: update_dre.py [--dry-run]
"""

import sys
import json
import subprocess
import os
from datetime import datetime

# Sheets
TX_SHEET = "1wHAon2Q-q-47uCBq0N-QVThktq1j6pn6UugwAwhGUY8"
TX_TAB = "IS160370266501246501212600"
DRE_SHEET = "112cV3ac8s1ex0tLKQhLheJwTIaCavoRDnmcCdEABoI4"
GOG_ACCOUNT = "lucasmpramos@gmail.com"

env = {**os.environ, "GOG_ACCOUNT": GOG_ACCOUNT}

# Category mapping: Transaction Sheet category → (DRE category, Income or Expenses tab)
CATEGORY_MAP = {
    # Income
    'Transfer': ('Other Income', 'Income'),
    'Collection': ('Other Income', 'Income'),
    # Salaries
    'Payroll Service': ('Salaries & Contractors', 'Expenses'),
    # Software
    'Software': ('Software & Tools', 'Expenses'),
    'Software — Design': ('Software & Tools', 'Expenses'),
    # Bank / Loan
    'Bank Fee': ('Bank Fees', 'Expenses'),
    'Loan Payment': ('Bank Fees', 'Expenses'),
    'Overdraft interest': ('Bank Fees', 'Expenses'),
    'Service fee': ('Bank Fees', 'Expenses'),
    # Office
    'Insurance': ('Office & Admin', 'Expenses'),
    'Pension Fund': ('Office & Admin', 'Expenses'),
    # Special
    'Thor Personal': ('Thor Personal', 'Expenses'),
    # Fallback
    'Uncategorized': ('Other Expense', 'Expenses'),
    'Entertainment': ('Other Expense', 'Expenses'),
}

# DRE category list (for validation)
INCOME_CATEGORIES = ['Retainer', 'Project', 'Other Income']
EXPENSE_CATEGORIES = ['Salaries & Contractors', 'Revenue Share', 'Software & Tools',
                      'Marketing', 'Office & Admin', 'Taxes', 'Bank Fees',
                      'Thor Personal', 'Other Expense']
ALL_CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES


def gog_read(sheet_id, range_str):
    """Read a range from a sheet."""
    result = subprocess.run(
        ["gog", "sheets", "read", sheet_id, range_str, "--json"],
        capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        print(f"ERROR reading sheet: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout).get('values', [])


def gog_write(sheet_id, range_str, data):
    """Write data to a sheet range."""
    result = subprocess.run(
        ["gog", "sheets", "update", sheet_id, range_str,
         "--values-json", json.dumps(data), "--no-input"],
        capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        print(f"ERROR writing sheet: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout.strip())


def make_dre_key(date_str, payee, amount):
    """Create a dedup key from date + payee + amount."""
    return f"{date_str}|{payee}|{amount}"


def parse_date(date_str):
    """Parse various date formats to DD/MM/YYYY."""
    date_str = str(date_str).strip()
    for fmt in ('%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_str, fmt).strftime('%d/%m/%Y')
        except ValueError:
            continue
    return date_str


def update_dre(dry_run=False):
    """Main DRE update logic."""
    print("=== Snowhouse DRE Update ===\n")

    # 1. Read all transactions from Transaction Sheet
    print("Reading Transaction Sheet...")
    tx_rows = gog_read(TX_SHEET, f"'{TX_TAB}'!A5:T500")

    # 2. Read existing DRE Income and Expenses rows for dedup
    print("Reading DRE Income tab...")
    income_rows = gog_read(DRE_SHEET, "'Income'!A2:F500")
    print(f"  {len([r for r in income_rows if r and r[0]])} existing Income rows")

    print("Reading DRE Expenses tab...")
    expense_rows = gog_read(DRE_SHEET, "'Expenses'!A2:F500")
    print(f"  {len([r for r in expense_rows if r and r[0]])} existing Expenses rows")

    # Build dedup sets
    income_keys = set()
    for r in income_rows:
        if r and r[0]:
            income_keys.add(make_dre_key(r[0], r[1], r[2]))

    expense_keys = set()
    for r in expense_rows:
        if r and r[0]:
            expense_keys.add(make_dre_key(r[0], r[1], r[2]))

    # 3. Process transactions
    new_income = []
    new_expenses = []
    skipped = 0
    unmapped = []

    for tx in tx_rows:
        if not tx or not tx[0]:
            continue
        while len(tx) < 20:
            tx.append('')

        date = parse_date(tx[0])
        description = str(tx[5]).strip()
        amount_usd = str(tx[3]).replace(',', '').replace('$', '').strip()
        category = str(tx[9]).strip()

        if not amount_usd or not category:
            continue

        try:
            amount = float(amount_usd)
        except ValueError:
            continue

        # Determine direction
        if amount > 0:
            # Income — use description as client
            dre_cat = 'Other Income'  # Default for positive amounts
            tab = 'Income'
            payee = description
            abs_amount = f"${amount:,.2f}"
            dedup_set = income_keys
        else:
            # Expense — map category
            mapped = CATEGORY_MAP.get(category)
            if not mapped:
                unmapped.append((date, description, category, amount))
                dre_cat = 'Other Expense'
            else:
                dre_cat = mapped[0]
            tab = 'Expenses'
            payee = description
            abs_amount = f"${abs(amount):,.2f}"
            dedup_set = expense_keys

        # Dedup check
        key = make_dre_key(date, payee, abs_amount)
        if key in dedup_set:
            skipped += 1
            continue

        row = [date, payee, abs_amount, 'USD', dre_cat, '']
        if tab == 'Income':
            new_income.append(row)
            income_keys.add(key)
        else:
            new_expenses.append(row)
            expense_keys.add(key)

    print(f"\nTransactions processed: {len([t for t in tx_rows if t and t[0]])} total")
    print(f"  New Income: {len(new_income)}")
    print(f"  New Expenses: {len(new_expenses)}")
    print(f"  Skipped (duplicate): {skipped}")

    if unmapped:
        print(f"\n⚠️  Unmapped categories ({len(unmapped)}):")
        for date, desc, cat, amt in unmapped[:10]:
            print(f"  {date} | {desc[:25]:25} | {cat:20} | ${amt:,.2f}")

    if dry_run:
        print("\nDry run — no changes written.")
        return

    # 4. Write new rows (APPEND to existing data)
    if new_income:
        existing_count = len([r for r in income_rows if r and r[0]])
        start_row = existing_count + 2  # +1 for header, +1 for 1-indexed
        gog_write(DRE_SHEET, f"'Income'!A{start_row}:F{start_row + len(new_income) - 1}", new_income)
        print(f"\n✅ Inserted {len(new_income)} Income rows")

    if new_expenses:
        existing_count = len([r for r in expense_rows if r and r[0]])
        start_row = existing_count + 2
        gog_write(DRE_SHEET, f"'Expenses'!A{start_row}:F{start_row + len(new_expenses) - 1}", new_expenses)
        print(f"✅ Inserted {len(new_expenses)} Expenses rows")

    if not new_income and not new_expenses:
        print("\nNothing new to insert.")

    print("\nDRE SUMIFS formulas auto-update. Check DRE tab for updated totals.")


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    update_dre(dry_run)
