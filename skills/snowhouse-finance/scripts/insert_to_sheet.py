#!/usr/bin/env python3
"""Insert categorized rows into the Snowhouse Google Sheet.

CRITICAL DESIGN DECISIONS (learned from Apr 15 incident):
1. ALWAYS reads the entire sheet, inserts new rows, and writes back ALL rows
2. NEVER uses gog sheets update on a partial range (causes overwrites)
3. Deduplicates by Unique Key (col T) BEFORE insertion
4. Validates USD amounts after insertion (sanity checks)
5. Preserves sort order (date descending)

Usage: insert_to_sheet.py <parsed_categorized.json>
"""

import sys
import json
import subprocess
import os

SHEET_ID = "1wHAon2Q-q-47uCBq0N-QVThktq1j6pn6UugwAwhGUY8"
SHEET_NAME = "IS160370266501246501212600"
GOG_ACCOUNT = "lucasmpramos@gmail.com"
RATE = 0.00807

env = {**os.environ, "GOG_ACCOUNT": GOG_ACCOUNT}


def gog_sheets_read(range_str):
    """Read a range from the sheet, return parsed JSON."""
    result = subprocess.run(
        ["gog", "sheets", "read", SHEET_ID, f"'{SHEET_NAME}'!{range_str}", "--json"],
        capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        print(f"ERROR reading sheet: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout).get('values', [])


def gog_sheets_write(range_str, data):
    """Write data to sheet range."""
    result = subprocess.run(
        ["gog", "sheets", "update", SHEET_ID, f"'{SHEET_NAME}'!{range_str}",
         "--values-json", json.dumps(data), "--no-input"],
        capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        print(f"ERROR writing sheet: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout.strip())


def get_existing_keys(sheet_rows):
    """Extract unique keys from sheet rows (col T, index 19)."""
    keys = set()
    for r in sheet_rows:
        if r and len(r) > 19 and r[19]:
            keys.add(str(r[19]))
    return keys


def deduplicate(new_rows, existing_keys):
    """Remove rows whose unique key already exists in the sheet."""
    to_add = []
    skipped = 0
    for row in new_rows:
        key = str(row[19]) if len(row) > 19 else ''
        if key and key in existing_keys:
            skipped += 1
        else:
            to_add.append(row)
    return to_add, skipped


def validate_usd(row):
    """Sanity check USD conversion for a single row.
    Returns list of warnings."""
    warnings = []
    try:
        amt_isk = float(str(row[1]).replace(',', ''))
        amt_usd = float(str(row[3]).replace(',', ''))
        bal_isk = float(str(row[2]).replace(',', ''))
        bal_usd = float(str(row[4]).replace(',', ''))

        expected_amt = round(amt_isk * RATE, 2)
        expected_bal = round(bal_isk * RATE, 2)

        if abs(amt_usd - expected_amt) > 1:
            warnings.append(f"Amount USD wrong: {amt_usd} (expected {expected_amt}) for {row[5]}")
        if abs(bal_usd - expected_bal) > 1:
            warnings.append(f"Balance USD wrong: {bal_usd} (expected {expected_bal}) for {row[5]}")

        # Flag unreasonable amounts (> $10k for a single debit card transaction)
        desc = str(row[5]).lower()
        type_en = str(row[8]).lower()
        if 'debit card' in type_en and abs(amt_usd) > 10000:
            warnings.append(f"SUSPICIOUS: ${amt_usd:,.2f} on debit card ({row[5]})")
    except (ValueError, IndexError):
        warnings.append(f"Could not validate row: {row[:6]}")
    return warnings


def insert_rows(new_rows_json_path):
    """Main insertion logic."""
    # 1. Read new rows from file
    with open(new_rows_json_path) as f:
        new_rows = json.load(f)

    if not new_rows:
        print("No rows in input file.")
        return

    # 2. Validate USD amounts BEFORE touching the sheet
    all_warnings = []
    for row in new_rows:
        warnings = validate_usd(row)
        all_warnings.extend(warnings)

    if all_warnings:
        print("\n⚠️  VALIDATION WARNINGS:")
        for w in all_warnings:
            print(f"  - {w}")
        print("\nAborting to prevent data corruption. Fix warnings above first.")
        sys.exit(1)

    # 3. Read entire current sheet
    print("Reading current sheet...")
    sheet_rows = gog_sheets_read("A5:T500")

    # 4. Deduplicate
    existing_keys = get_existing_keys(sheet_rows)
    to_add, skipped = deduplicate(new_rows, existing_keys)

    print(f"Sheet has {len(sheet_rows)} rows, {len(existing_keys)} unique keys")
    print(f"Input: {len(new_rows)} rows, {skipped} duplicates, {len(to_add)} new")

    if not to_add:
        print("\nNothing to insert — all records already exist.")
        return

    # 5. Prepend new rows (sheet is sorted date descending, new rows should be newer)
    final = to_add + sheet_rows
    print(f"\nInserting {len(to_add)} new rows at top. Total: {len(final)} rows")

    # 6. Write ENTIRE sheet back (never partial!)
    gog_sheets_write(f"A5:T{4 + len(final)}", final)

    # 7. Verify by reading back and checking new rows
    print("\nVerifying...")
    verify_rows = gog_sheets_read(f"A5:T{4 + len(to_add)}")
    errors = 0
    for i, (expected, actual) in enumerate(zip(to_add, verify_rows)):
        if expected != actual:
            print(f"  MISMATCH row {i+5}: expected {expected[:5]}, got {actual[:5] if actual else 'EMPTY'}")
            errors += 1

    if errors:
        print(f"\n❌ {errors} rows didn't match after insertion!")
    else:
        print(f"\n✅ Done — {len(to_add)} rows inserted and verified.")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: insert_to_sheet.py <parsed_categorized.json>")
        sys.exit(1)

    insert_rows(sys.argv[1])
