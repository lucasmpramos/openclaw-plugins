#!/usr/bin/env python3
"""Parse Arion Bank xlsx statement and output structured JSON for insertion."""

import sys
import json
from datetime import datetime
from openpyxl import load_workbook

def parse(filepath, exchange_rate=None):
    wb = load_workbook(filepath)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    
    # Find header row (contains 'Dagsetning')
    header_idx = None
    for i, row in enumerate(rows[:6]):
        if row and 'Dagsetning' in str(row):
            header_idx = i
            break
    
    if header_idx is None:
        print("ERROR: Could not find header row with 'Dagsetning'", file=sys.stderr)
        sys.exit(1)
    
    headers = rows[header_idx]
    data_rows = rows[header_idx + 1:]
    
    records = []
    for row in data_rows:
        if not row[0]:
            continue
        
        date = row[0].strftime('%d.%m.%Y') if isinstance(row[0], datetime) else str(row[0])
        
        records.append({
            'date': date,
            'amount_isk': row[1] or 0,
            'balance_isk': row[2] or 0,
            'currency': row[3] or 'ISK',
            'description': row[4] or '',
            'receipt_no': row[5] or '',
            'reference': row[6] or '',
            'type': row[7] or '',
            'transaction_key': str(row[8] or ''),
            'interest_day': str(row[9] or ''),
            'text_key': str(row[10] or ''),
            'payment_bank': str(row[11] or ''),
            'batch_no': str(row[12] or ''),
            'interest_date': str(row[13] or ''),
            'recipient': str(row[14] or '') if len(row) > 14 else '',
            'number': str(row[15] or '') if len(row) > 15 else '',
            'recipient_id': str(row[16] or '') if len(row) > 16 else '',
            'unique_key': str(row[17] or '') if len(row) > 17 else '',
        })
    
    # Sort by date descending (newest first)
    records.sort(key=lambda r: r['date'], reverse=True)
    
    # Add USD conversions if rate provided
    if exchange_rate:
        for r in records:
            r['amount_usd'] = round(r['amount_isk'] * exchange_rate, 2)
            r['balance_usd'] = round(r['balance_isk'] * exchange_rate, 2)
    
    return records

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: parse_bank_statement.py <file.xlsx> [--rate 0.00807]")
        sys.exit(1)
    
    filepath = sys.argv[1]
    rate = None
    
    if '--rate' in sys.argv:
        rate = float(sys.argv[sys.argv.index('--rate') + 1])
    
    records = parse(filepath, rate)
    
    dates = [r['date'] for r in records]
    print(f"Parsed {len(records)} transactions: {dates[-1]} to {dates[0]}")
    
    outpath = filepath.replace('.xlsx', '_parsed.json')
    if outpath == filepath:
        outpath = filepath + '_parsed.json'
    
    with open(outpath, 'w') as f:
        json.dump(records, f, indent=2)
    print(f"Saved to {outpath}")
