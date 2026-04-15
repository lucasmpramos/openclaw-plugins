#!/usr/bin/env python3
"""Categorize parsed bank transactions and prepare rows for Google Sheets insertion.

Reads categories from references/categories.md (relative to skill directory).
Outputs rows ready for gog sheets update or direct API insertion.
"""

import sys
import json
import re
import os

# --- Type translations ---
TYPE_MAP = {
    'Debitkortafærsla': 'Debit card',
    'Innborgun': 'Deposit',
    'Laun': 'Salary',
    'Símgreiðsla': 'Online banking',
    'Millifært': 'Transfer',
    'Innheimtukrafa': 'Collection claim',
    'Innheimtukrafa - kostnaður': 'Collection fee',
    'Bifreiðagjald': 'Vehicle tax',
    'Kílómetragjald': 'Mileage tax',
    'Greiðsludreifing': 'Payment plan',
    'Staðgreiðsluskattur': 'Withholding tax',
    'Tryggingar': 'Insurance',
    'Útborgun': 'Disbursement',
    'Lýsing': 'Leasing',
    'Útvextir': 'Overdraft interest',
    'Þjónustugjald': 'Service fee',
    'Reikningur': 'Invoice',
    'Árgjald': 'Annual fee',
    'Greiðsluáætlun': 'Payment schedule',
    'Innheimt': 'Collection',
}

# --- Vendor → Category rules ---
VENDOR_RULES = [
    # Software — AI
    (r'claude|chatgpt|openai', 'Software — AI'),
    # Software — Web Dev
    (r'webflow', 'Software — Web Dev'),
    # Software — Design
    (r'relume|figma', 'Software — Design'),
    # Software — Invoicing
    (r'bonsai', 'Software — Invoicing'),
    # Software — Marketing
    (r'x corp|typefully', 'Software — Marketing'),
    # Software (general)
    (r'slack|clickup|todoist|setapp|paddle|dropbox', 'Software'),
    # Income — PayPal
    (r'paypal', 'Income — PayPal'),
    # Bank Fee
    (r'arion banki', 'Bank Fee'),
    # Loan Payment
    (r'lykill', 'Loan Payment'),
    # Collections
    (r'innheimtuþjónusta', 'Collections'),
    # Insurance
    (r'tm tryggingar|sjóvá', 'Insurance'),
    # Pension/Tax
    (r'gildi|lífeyris', 'Pension/Tax'),
    # Telecom
    (r'síminn|nova hf|nova\b', 'Telecom'),
    # Transport — Fuel
    (r'orkan|atlantsolía|atlantsolía', 'Transport — Fuel'),
    # Transport — Parking
    (r'bílastæðasjóður', 'Transport — Parking'),
    # Payroll
    (r'payday', 'Payroll Service'),
    # Entertainment
    (r'viaplay|harpa|youtube|playstation', 'Entertainment'),
    # Fitness
    (r'crossfit|sudurbaejarlaug', 'Fitness'),
    # Membership
    (r'samtök vefiðnaðarins', 'Membership'),
    # Professional Services
    (r'altagency', 'Professional Services'),
    # Food & Dining
    (r'aktu taktu', 'Food & Dining'),
    # Transfer (CI000 references — Icelandic online banking)
    (r'^CI\d+$', 'Transfer'),
]


def categorize(description, type_raw):
    """Categorize a transaction by description and type."""
    desc = (description or '').lower()
    
    for pattern, category in VENDOR_RULES:
        if re.search(pattern, desc, re.IGNORECASE):
            return category
    
    return 'Uncategorized'


def translate_type(type_raw):
    """Translate Icelandic type to English."""
    return TYPE_MAP.get(type_raw, type_raw or '')


def enrich_description(desc):
    """Add English context to Icelandic descriptions."""
    if not desc:
        return ''
    
    enrichments = {
        'lykill fjármögnun': 'Lykill fjármögnun (loan/leasing)',
        'bílastæðasjóður': 'Bílastæðasjóður (parking fee)',
        'gildi': 'Gildi pension fund',
        'samtök vefiðnaðarins': 'Web Industry Association',
        'innheimtuþjónusta': 'Collection service',
        'tm tryggingar': 'TM Insurance',
        'sjóvá-almennar': 'Sjóvá-Almennar (insurance)',
    }
    
    for icelandic, english in enrichments.items():
        if icelandic.lower() in desc.lower():
            return english
    return desc


def process(records, exchange_rate):
    """Process parsed records into sheet-ready rows."""
    rows = []
    uncategorized = []
    
    for r in records:
        amt_isk = r.get('amount_isk', 0) or 0
        bal_isk = r.get('balance_isk', 0) or 0
        rate = exchange_rate or 0.00807
        amt_usd = round(amt_isk * rate, 2)
        bal_usd = round(bal_isk * rate, 2)
        
        type_en = translate_type(r.get('type', ''))
        category = categorize(r.get('description', ''), r.get('type', ''))
        desc = enrich_description(r.get('description', ''))
        
        if category == 'Uncategorized':
            uncategorized.append(r)
        
        row = [
            r.get('date', ''),
            f"{amt_isk:,.2f}",
            f"{bal_isk:,.2f}",
            f"{amt_usd:,.2f}",
            f"{bal_usd:,.2f}",
            desc,
            str(r.get('receipt_no', '')),
            str(r.get('reference', '')),
            type_en,
            category,
            str(r.get('transaction_key', '')),
            str(r.get('interest_day', '')),
            str(r.get('text_key', '')),
            str(r.get('payment_bank', '')),
            str(r.get('batch_no', '')),
            str(r.get('interest_date', '')),
            str(r.get('recipient', '')),
            str(r.get('number', '')),
            str(r.get('recipient_id', '')),
            str(r.get('unique_key', '')),
        ]
        rows.append(row)
    
    return rows, uncategorized


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: categorize.py <parsed.json> [--rate 0.00807]")
        sys.exit(1)
    
    with open(sys.argv[1]) as f:
        records = json.load(f)
    
    rate = None
    if '--rate' in sys.argv:
        rate = float(sys.argv[sys.argv.index('--rate') + 1])
    
    rows, uncategorized = process(records, rate)
    
    print(f"Processed {len(rows)} rows")
    if uncategorized:
        print(f"\n⚠️  {len(uncategorized)} UNCATEGORIZED:")
        for r in uncategorized:
            print(f"  {r['date']} | {r['amount_isk']:>12,} ISK | {r['description'][:40]}")
    
    outpath = sys.argv[1].replace('_parsed.json', '_rows.json')
    with open(outpath, 'w') as f:
        json.dump(rows, f)
    print(f"\nRows saved to {outpath}")
