# -*- coding: utf-8 -*-
"""
auto_header.py
==============
Generically detects the header row in a bank statement sheet by scanning
for rows that contain both a date-type keyword and an amount-type keyword.

No bank-specific knowledge is used — works for any tabular statement.
"""

from __future__ import annotations

# Keywords that indicate a "date" column header
_DATE_KEYS = {'date', 'txn date', 'tran date', 'transaction date', 'value date',
               'value dt', 'srl no', 'sl. no.', 'sl no'}

# Keywords that indicate an "amount" column header
_AMT_KEYS  = {'debit', 'credit', 'withdrawal', 'deposit', 'dr', 'cr',
               'amount', 'balance', 'withdrawals', 'deposits',
               'withdrawal amt', 'withdrawal amt.', 'deposit amt', 'deposit amt.',
               'closing balance'}


def find_header_row(sheet_rows: list[tuple]) -> int:
    """
    Scan rows top-to-bottom and return the 0-based index of the first row that:
      - Has ≥ 4 non-null, non-empty cells
      - Contains at least one cell matching a *date-type* keyword
      - Contains at least one cell matching an *amount-type* keyword
      - Total keyword matches ≥ 3  (avoids false-positive on metadata rows like
        'Opening Balance, Date of Issue')

    Falls back to 0 if nothing qualifies.
    """
    for i, row in enumerate(sheet_rows):
        # Collect non-null, non-empty cell values as lowercase strings
        cells = [str(c).strip().lower() for c in row
                 if c is not None and str(c).strip() not in ('', 'nan', 'none')]

        if len(cells) < 4:
            continue

        date_matches = sum(1 for c in cells
                           if c in _DATE_KEYS or any(dk in c for dk in _DATE_KEYS))
        amt_matches  = sum(1 for c in cells
                           if c in _AMT_KEYS  or any(ak in c for ak in _AMT_KEYS))

        if date_matches >= 1 and amt_matches >= 1 and (date_matches + amt_matches) >= 3:
            return i

    return 0  # safe fallback
