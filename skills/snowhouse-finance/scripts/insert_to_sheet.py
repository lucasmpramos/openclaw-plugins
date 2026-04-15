#!/usr/bin/env python3
"""Insert categorized rows into the Snowhouse Google Sheet.

Requires: gog CLI authenticated, openpyxl installed.
Handles deduplication via Unique Key column (T).
"""

import sys
import json
import subprocess
import os

SHEET_ID = "1wHAon2Q-q-47uCBq0N-QVThktq1j6pn6UugwAwhGUY8"
SHEET_NAME = "IS160370266501246501212600"
GOG_ACCOUNT = "lucasmpramos@gmail.com"


def get_existing_keys():
    """Fetch existing unique keys from the sheet."""
    result = subprocess.run(
        ["gog", "sheets", "read", SHEET_ID, f"'{SHEET_NAME}'!T5:T500", "--json"],
        capture_output=True, text=True, env={**os.environ, "GOG_ACCOUNT": GOG_ACCOUNT}
    )
    data = json.loads(result.stdout)
    keys = set()
    for r in data.get('values', []):
        if r and r[0]:
            keys.add(str(r[0]))
    return keys


def deduplicate(rows_json_path, existing_keys):
    """Remove rows whose unique key already exists in the sheet."""
    with open(rows_json_path) as f:
        rows = json.load(f)
    
    new_rows = []
    skipped = 0
    for row in rows:
        # Unique key is column T (index 19)
        if len(row) > 19 and row[19] and str(row[19]) in existing_keys:
            skipped += 1
        else:
            new_rows.append(row)
    
    return new_rows, skipped


def get_access_token():
    """Get fresh Google access token via gog auth export."""
    # Export token
    token_path = "/tmp/gog_token_finance.json"
    subprocess.run(["gog", "auth", "export", token_path], capture_output=True)
    
    with open(token_path) as f:
        token_data = json.load(f)
    
    # Refresh using stored credentials
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
    
    with open('/tmp/gog_access_token.txt', 'w') as f:
        f.write(result['access_token'])
    
    return result['access_token']


def insert_rows(rows, access_token):
    """Insert rows at top of sheet (row 5) using Google Sheets API."""
    if not rows:
        print("No new rows to insert.")
        return
    
    count = len(rows)
    print(f"Inserting {count} rows...")
    
    # Get sheet tab ID
    import urllib.request
    req = urllib.request.Request(
        f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets.properties"
    )
    req.add_header('Authorization', f'Bearer {access_token}')
    resp = urllib.request.urlopen(req)
    sheets = json.loads(resp.read())['sheets']
    tab_id = None
    for s in sheets:
        if 'IS16' in s['properties']['title']:
            tab_id = s['properties']['sheetId']
            break
    
    if tab_id is None:
        print("ERROR: Could not find sheet tab", file=sys.stderr)
        sys.exit(1)
    
    # Insert empty rows at row 5 (startIndex 4)
    insert_body = json.dumps({
        "requests": [{
            "insertDimension": {
                "range": {
                    "sheetId": tab_id,
                    "dimension": "ROWS",
                    "startIndex": 4,
                    "endIndex": 4 + count
                },
                "inheritFromBefore": False
            }
        }]
    }).encode()
    
    req = urllib.request.Request(
        f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate",
        data=insert_body,
        method='POST'
    )
    req.add_header('Authorization', f'Bearer {access_token}')
    req.add_header('Content-Type', 'application/json')
    urllib.request.urlopen(req)
    print(f"Inserted {count} empty rows.")
    
    # Write data via gog CLI
    env = {**os.environ, "GOG_ACCOUNT": GOG_ACCOUNT}
    range_str = f"'{SHEET_NAME}'!A5:T{4 + count}"
    
    # gog expects JSON array of arrays
    rows_json = json.dumps(rows)
    result = subprocess.run(
        ["gog", "sheets", "update", SHEET_ID, range_str, "--values-json", rows_json, "--no-input"],
        capture_output=True, text=True, env=env
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}", file=sys.stderr)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: insert_to_sheet.py <rows.json>")
        sys.exit(1)
    
    print("Fetching existing keys for deduplication...")
    existing_keys = get_existing_keys()
    print(f"Sheet has {len(existing_keys)} existing keys.")
    
    new_rows, skipped = deduplicate(sys.argv[1], existing_keys)
    print(f"New rows: {len(new_rows)}, Skipped (duplicate): {skipped}")
    
    if new_rows:
        token = get_access_token()
        insert_rows(new_rows, token)
        print(f"\n✅ Done — {len(new_rows)} rows inserted into sheet.")
    else:
        print("\nNothing to insert — all records already exist.")
