#!/usr/bin/env python3
"""Recalculate and validate ALL USD columns in the sheet.

Fixes Amount USD (col D) and Balance USD (col E) by recalculating from
Amount ISK (col B) and Balance ISK (col C) × exchange rate.

Usage: fix_usd.py [--rate 0.00807] [--dry-run]
"""

import sys
import json
import subprocess
import os

SHEET_ID = "1wHAon2Q-q-47uCBq0N-QVThktq1j6pn6UugwAwhGUY8"
SHEET_NAME = "IS160370266501246501212600"
GOG_ACCOUNT = "lucasmpramos@gmail.com"

env = {**os.environ, "GOG_ACCOUNT": GOG_ACCOUNT}


def gog_read(range_str):
    result = subprocess.run(
        ["gog", "sheets", "read", SHEET_ID, f"'{SHEET_NAME}'!{range_str}", "--json"],
        capture_output=True, text=True, env=env
    )
    return json.loads(result.stdout).get('values', [])


def gog_write(range_str, data):
    result = subprocess.run(
        ["gog", "sheets", "update", SHEET_ID, f"'{SHEET_NAME}'!{range_str}",
         "--values-json", json.dumps(data), "--no-input"],
        capture_output=True, text=True, env=env
    )
    print(result.stdout.strip())


def fix(rate=0.00807, dry_run=False):
    rows = gog_read("A5:T500")
    fixed = 0

    for i, r in enumerate(rows):
        if not r or not r[0]:
            continue
        while len(r) < 20:
            r.append('')

        amt_isk_str = str(r[1]).replace(',', '').strip()
        bal_isk_str = str(r[2]).replace(',', '').strip()

        if not amt_isk_str:
            continue

        try:
            amt_isk = float(amt_isk_str)
            bal_isk = float(bal_isk_str) if bal_isk_str else None
        except ValueError:
            continue

        expected_amt_usd = round(amt_isk * rate, 2)
        expected_bal_usd = round(bal_isk * rate, 2) if bal_isk is not None else None

        changed = False

        # Fix Amount USD (col 3)
        current_amt_usd = r[3].strip() if r[3] else ''
        if current_amt_usd:
            try:
                if abs(float(current_amt_usd.replace(',', '')) - expected_amt_usd) > 0.5:
                    print(f"Row {i+5}: {str(r[5])[:25]:25} | amt_usd {r[3]:>12} → {expected_amt_usd:>12,.2f}")
                    r[3] = f"{expected_amt_usd:,.2f}"
                    changed = True
            except ValueError:
                r[3] = f"{expected_amt_usd:,.2f}"
                changed = True

        # Fix Balance USD (col 4)
        if expected_bal_usd is not None:
            current_bal_usd = r[4].strip() if r[4] else ''
            if current_bal_usd:
                try:
                    if abs(float(current_bal_usd.replace(',', '')) - expected_bal_usd) > 0.5:
                        print(f"Row {i+5}: {str(r[5])[:25]:25} | bal_usd {r[4]:>12} → {expected_bal_usd:>12,.2f}")
                        r[4] = f"{expected_bal_usd:,.2f}"
                        changed = True
                except ValueError:
                    r[4] = f"{expected_bal_usd:,.2f}"
                    changed = True
            else:
                r[4] = f"{expected_bal_usd:,.2f}"
                changed = True

        if changed:
            fixed += 1

    print(f"\n{fixed} values need fixing.")

    if dry_run:
        print("Dry run — no changes written.")
        return

    if fixed > 0:
        gog_write(f"A5:T{4 + len(rows)}", rows)
        print(f"✅ Fixed {fixed} USD values.")
    else:
        print("✅ All USD values are correct.")


if __name__ == '__main__':
    rate = 0.00807
    dry_run = '--dry-run' in sys.argv

    if '--rate' in sys.argv:
        rate = float(sys.argv[sys.argv.index('--rate') + 1])

    fix(rate, dry_run)
