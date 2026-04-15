---
name: snowhouse-finance
description: Parse, translate, categorize, and insert Icelandic bank transactions (Arion Bank) into a Google Sheet for Snowhouse financial tracking. Use when: (1) Luke uploads an Icelandic bank statement xlsx, (2) Luke asks to add new transactions to the Snowhouse sheet, (3) Luke asks about Snowhouse expenses/income/balance, (4) Luke mentions Arion Bank, ISK, or the Snowhouse Google Sheet. Triggers on "bank statement", "transactions", "Arion", "ISK", "snowhouse finance", "add to sheet", "update sheet".
---

# Snowhouse Finance

Pipeline: xlsx → parse → translate Icelandic → ISK→USD → categorize → deduplicate → insert into Google Sheet → update summary.

## Quick Start

1. Download the xlsx from Slack (use `message download-file` with Slack bot token auth)
2. Run `scripts/parse_bank_statement.py /path/to/file.xlsx`
3. Review output — especially "Uncategorized" rows
4. Run `scripts/insert_to_sheet.py /path/to/parsed.json`
5. Run `scripts/update_summary.py`

## Sheet Details

- **Sheet ID:** `1wHAon2Q-q-47uCBq0N-QVThktq1j6pn6UugwAwhGUY8`
- **Tab:** `IS160370266501246501212600` (Arion Bank IS16 0370 2665 0124 6501 2126 00)
- **Summary Tab:** `Category Summary`
- **Columns (A-T):** Date, Amount ISK, Balance ISK, Amount USD, Balance USD, Description, Receipt No., Reference, Type, Category (BOB), Transaction Key, Interest Day, Text Key, Payment Bank, Batch No., Interest Date, Recipient/Payer Name, Number, Recipient/Payer ID, Unique Key

## Exchange Rate

Use the **closing ISK/USD rate for the statement month**. Ask Luke if not provided. Store the rate used in the summary tab.

## Column Layout in xlsx

Raw Arion exports have rows 0-2 as metadata, row 3 as headers (Icelandic), row 4+ as data. Headers:

`Dagsetning` (Date), `Upphæð` (Amount), `Staða` (Balance), `Mynt` (Currency), `Skýring` (Description), `Seðilnúmer` (Receipt No.), `Tilvísun` (Reference), `Texti` (Type), `Færslulykill` (Transaction Key), `Vaxtadagur` (Interest Day), `Textalykill` (Text Key), `Greiðslubanki` (Payment Bank), `Bunkanúmer` (Batch No.), `Vaxtadagsetning` (Interest Date), `Nafn viðtakanda eða greiðanda` (Recipient/Payer), `Númer` (Number), `Kennitala viðtakanda eða greiðanda` (Recipient/Payer ID), `Einkvæmur lykill` (Unique Key)

## Deduplication

Use column T (Unique Key) to check against existing sheet data. Only insert rows whose unique key is not already present.

## Google Sheets API Auth

`gog sheets` CLI only supports read/update ranges. For row insertion (batchUpdate/insertDimension), use the direct API:

1. Export token: `gog auth export /tmp/gog_token.json`
2. Extract refresh_token
3. Use Python `google.oauth2.credentials` to get access token
4. `curl` with Bearer token for `batchUpdate` calls

Account: `lucasmpramos@gmail.com`

## Categorization

See `references/categories.md` for the full vendor→category mapping and type translations. New vendors go to "Uncategorized" for Luke's review — once categorized, add to the mapping file.

## Bonsai Invoices

Bonsai posts invoice lifecycle events to the Slack channel. Parse from channel history when needed. Pages behind Cloudflare (403) — rely on bot messages only.
