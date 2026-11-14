# Onboarding and validation

New entities use `config/entities/<id>.json`. Give every account a unique
`account_key`, `account_id`, and `sheet_name`. Several accounts may share the
same `bank` value; this value selects `config/banks/<bank>.json` and its rules.
Use `meta_signals_extra` for account-specific statement identifiers.

The consolidation map at `config/consolidation/<entity>_<fy>.json` contains:

```json
{
  "files": [
    {
      "filename": "statement.xlsx",
      "sheet_name": "Savings 1234",
      "source_sheet": "Transactions",
      "password_env_var": "OPTIONAL_PASSWORD_VARIABLE"
    }
  ]
}
```

Omit `password_env_var` for unencrypted files. Excel consolidation inventories
and imports **all non-empty worksheets by default**, including hidden worksheets.
A multi-bank file needs only its filename. Each sheet resolves to the account's
configured sheet name using exact names/aliases, a unique bank name, or metadata
fingerprints. An unresolved or ambiguous sheet fails instead of disappearing.

Use `sheet_map` to declare source-to-target names when automatic resolution is
insufficient. `exclude_sheets` explicitly excludes non-statement tabs. Optional
`source_sheet` (name or zero-based index) deliberately selects one worksheet;
other worksheets are still inventoried as skipped. `sheet_name` sets the target
when only one worksheet is selected. Duplicate target accounts across files fail:
choose one authoritative source, rather than importing XLSX plus duplicate PDFs.
The generated `consolidation_manifest.json` lists every source sheet, its target
and row count, or its skip reason. Empty and excluded sheets are recorded.

CSV entries optionally accept `delimiter` and `encoding` (defaults: comma and
UTF-8 with optional BOM). Quoted multiline fields are supported. Banks with a
single signed amount layout can declare `col_amount`, `col_direction` and the
zero-based `direction_column_occurrence`; this distinguishes transaction signs
from repeated balance-sign headers. Existing separate debit/credit columns win.

Use target sheet names that match entity account `sheet_name` values: these
provide explicit account bindings. Otherwise identification uses account
signals and bank fingerprints; tied matches fail instead of guessing.

PDF ingestion reads all extracted tables on all pages and removes repeated
identical table headers. Tables must have consistent column counts. A page
without an extractable table fails the import. Scanned PDFs, unrelated summary
tables, wrapped rows and unusual layouts may need a dedicated parser or a CSV
export; this is not an arbitrary-PDF extraction engine.

Entity profiles and declarative rule structures are validated at runtime.
Unknown bank definitions, invalid rules, missing mapped columns, missing input
files/password variables, duplicate account keys/target sheets and ambiguous
accounts fail processing. Pipeline API input/configuration errors return 422;
missing files return 404. No new final workbook is saved after an extraction or
classification failure; a workbook from an earlier run may still exist.

Bank/common rules and merchant dictionaries are read again on subsequent
processing calls. Rule chains are compiled once per input sheet. Do not edit
configuration during a run: the entire run is not a transactional configuration
snapshot. Header/scoring settings still require an API restart.

Rules match narration, debit and credit with first-match precedence. Inspect
priority when introducing broader patterns. Same-bank contra targets require
account digits; a bank name alone does not select a destination account.
Confidence values are configured scores, not measured probabilities. Contra
classification does not itself prove that a matching opposite entry exists.

Before accepting a new bank, check transaction counts, debit/credit totals,
dates, balances and review categories against original statements. Run:

```powershell
.venv\Scripts\python.exe -m unittest discover -s src/tax_automation/tests
```

The onboarding regression tests exercise an unseen synthetic bank/entity with
two accounts, rule reloads, ambiguous identities, incomplete input, CSV quoting,
explicit Excel sheet selection and mocked multipage PDF tables. Real bank PDF
fixtures are still needed to establish extraction accuracy for each format.


Person identity matching is shared by reconciliation, family classification and
self-transfer checks. It compares text spans for all declared names and aliases.
A complete name can include up to two additional middle-name tokens; contained
matches for another person's name are suppressed. Payment connectors such as TO,
FROM and AND and bank delimiters are not treated as middle names. Separate name
mentions and identical-name ties remain ambiguous. Use `identity_aliases` or an
explicit family `entity_id` for more complex names. There are no person-specific
exceptions in the matcher.

Cash-withdrawal rules marked `pre_identity: true` run before synthesized identity
rules, preventing ATM descriptions from being labelled as family/self transfers.
ATM/ATW/CWDR descriptions are also excluded from transfer reconciliation, even
when the ledger's existing label is incorrect. Recognition of `ATM-CASH` belongs
to the common rule configuration. A masked beneficiary with no readable name or
VPA can still legitimately fall through to UPI Payment; reconciliation proposes
a correction only from counterpart evidence, with the audit trail retained.
