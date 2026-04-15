#!/usr/bin/env python3
"""Recalculate and update the Category Summary tab.

Reads all data from the transactions tab, aggregates by category and month,
and writes updated totals to the Category Summary tab.
"""

import json
import subprocess
import os
from collections import defaultdict

SHEET_ID = "1wHAon2Q-q-47uCBq0N-QVThktq1j6pn6UugwAwhGUY8"
SHEET_NAME = "IS160370266501246501212600"
SUMMARY_TAB = "Category Summary"
GOG_ACCOUNT = "lucasmpramos@gmail.com"

MONTH_NAMES = {
    '01': 'January', '02': 'February', '03': 'March',
    '04': 'April', '05': 'May', '06': 'June',
    '07': 'July', '08': 'August', '09': 'September',
    '10': 'October', '11': 'November', '12': 'December'
}


def read_sheet_data():
    """Read all transaction data from the sheet."""
    result = subprocess.run(
        ["gog", "sheets", "read", SHEET_ID, f"'{SHEET_NAME}'!A5:T500", "--json"],
        capture_output=True, text=True, env={**os.environ, "GOG_ACCOUNT": GOG_ACCOUNT}
    )
    return json.loads(result.stdout).get('values', [])


def get_access_token():
    """Refresh Google access token."""
    token_path = "/tmp/gog_token_finance.json"
    subprocess.run(["gog", "auth", "export", token_path], capture_output=True)
    
    with open(token_path) as f:
        token_data = json.load(f)
    
    cred_path = os.path.expanduser("~/Library/Application Support/gogcli/credentials.json")
    with open(cred_path) as f:
        creds = json.load(f)
    
    import urllib.request, urllib.parse
    data = urllib.parse.urlencode({
        'client_id': creds['client_id'],
        'client_secret': creds['client_secret'],
        'refresh_token': token_data['refresh_token'],
        'grant_type': 'refresh_token'
    }).encode()
    
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    return result['access_token']


def update_summary_tab(access_token):
    """Recalculate and write summary data."""
    rows = read_sheet_data()
    
    # Aggregate by month and category
    monthly_data = defaultdict(lambda: defaultdict(lambda: {'spent_usd': 0, 'income_usd': 0, 'count': 0}))
    
    for row in rows:
        if not row or not row[0]:
            continue
        
        parts = row[0].split('.')
        if len(parts) != 3:
            continue
        
        month = MONTH_NAMES.get(parts[1], parts[1])
        
        try:
            amt_usd = float(str(row[3]).replace(',', '')) if len(row) > 3 and row[3] else 0
        except (ValueError, IndexError):
            continue
        
        category = row[9] if len(row) > 9 and row[9] else 'Uncategorized'
        
        monthly_data[month][category]['count'] += 1
        if amt_usd < 0:
            monthly_data[month][category]['spent_usd'] += abs(amt_usd)
        else:
            monthly_data[month][category]['income_usd'] += amt_usd
    
    # Calculate monthly totals
    monthly_totals = {}
    for month in ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']:
        if month not in monthly_data:
            continue
        spent = sum(d['spent_usd'] for d in monthly_data[month].values())
        income = sum(d['income_usd'] for d in monthly_data[month].values())
        monthly_totals[month] = {'spent': spent, 'income': income, 'balance': income - spent}
        print(f"{month}: Spent ${spent:,.2f} | Income ${income:,.2f} | Balance ${income - spent:,.2f}")
    
    total_spent = sum(m['spent'] for m in monthly_totals.values())
    total_income = sum(m['income'] for m in monthly_totals.values())
    print(f"\nTOTAL: Spent ${total_spent:,.2f} | Income ${total_income:,.2f} | Balance ${total_income - total_spent:,.2f}")
    
    # Write monthly balance rows to summary tab (update existing section)
    # Find how many months we have
    months_list = list(monthly_totals.keys())
    if not months_list:
        print("No data to write.")
        return
    
    # Build balance update — overwriting rows 46-48 (header + data + blank)
    header = ['']
    months_header = ['MONTHLY BALANCE (Income - Expenses)']
    col_headers = ['']
    col_data = ['']
    
    for m in months_list:
        col_headers[0] += f'{m[:3]} Spent | {m[:3]} Income | {m[:3]} Balance | '
        col_data[0] += f"{monthly_totals[m]['spent']:,.2f} | {monthly_totals[m]['income']:,.2f} | {monthly_totals[m]['balance']:,.2f} | "
    
    col_headers[0] += 'Total Spent | Total Income | Total Balance'
    col_data[0] += f"{total_spent:,.2f} | {total_income:,.2f} | {total_income - total_spent:,.2f}"
    
    # Use gog to update — put in column A only for simplicity
    env = {**os.environ, "GOG_ACCOUNT": GOG_ACCOUNT}
    for i, line in enumerate([months_header, [col_headers[0]], [col_data[0]]]):
        result = subprocess.run(
            ["gog", "sheets", "update", SHEET_ID, f"'{SUMMARY_TAB}'!A{46+i}:P{46+i}",
             "--values-json", json.dumps(line), "--no-input"],
            capture_output=True, text=True, env=env
        )
        if result.returncode != 0:
            print(f"Write error row {46+i}: {result.stderr}")
    
    print(f"\n✅ Summary tab updated with {len(months_list)} months of data.")


if __name__ == '__main__':
    token = get_access_token()
    update_summary_tab(token)
