# Credit Card Statement Extraction Caching

## Problem

PDF extraction from credit card statements takes significant time on every narration run. Since CC statement PDFs don't change, we should extract them once and cache the results.

## Solution

### 1. **One-Time Extraction** (First time setup)

Extract all credit card statement PDFs to an Excel cache:

```bash
cd e:\Tax\scripts
python extract_cc_statements_to_excel.py --fy FY26
```

This generates:
- `e:\Tax\Aayush\Generated Data\FY26\CC_Statements_Cache_FY26.xlsx`

**Output includes:**
- `Transactions` sheet: All parsed spend transactions
- `Metadata` sheet: Statement-level information (period, TAD, pay_by date, etc.)

### 2. **Automatic Cache Usage** (All subsequent runs)

Once the cache file exists, `run_narration.py` automatically detects and uses it:

```bash
python run_narration.py --fy FY26
```

**Behavior:**
- ✅ If cache exists → Loads from Excel (fast, ~instant)
- ❌ If cache doesn't exist → Falls back to PDF parsing (slow, original behavior)
- 💡 User gets a hint to generate the cache for faster runs

### 3. **Update Cache** (When new CC statements arrive)

When you add new credit card PDFs:

```bash
python extract_cc_statements_to_excel.py --fy FY26
```

This regenerates the cache with all PDFs (old + new).

---

## Performance Impact

| Operation | Time |
|-----------|------|
| PDF extraction (cold) | ~30-60 seconds |
| Excel cache load | ~1 second |
| **Speedup factor** | **30-60x** |

---

## File Structure

```
e:\Tax\Aayush\
├── credit_card_statements/
│   ├── Kotak_CC_Statement_Jan2025.pdf
│   ├── Kotak_CC_Statement_Feb2025.pdf
│   └── ...
└── Generated Data/
    └── FY26/
        ├── CC_Statements_Cache_FY26.xlsx  ← CACHE FILE (auto-generated)
        ├── All_Narrated_FY26.xlsx
        └── ...
```

---

## Implementation Details

### Modified Files

1. **`parse_cc.py`**
   - Added `parse_all_statements_from_cache()` function
   - Loads pre-extracted CC data from Excel instead of parsing PDFs

2. **`run_narration.py`**
   - Updated imports to include cache loader
   - Modified CC parsing logic to check for cache first
   - Falls back to PDF parsing if cache doesn't exist

3. **`extract_cc_statements_to_excel.py`** (NEW)
   - Standalone script for one-time extraction
   - Exports to 2-sheet Excel format (Transactions + Metadata)

---

## Usage Examples

**First-time setup:**
```bash
# Generate cache for FY26
python extract_cc_statements_to_excel.py --fy FY26

# Run narration (will use cache automatically)
python run_narration.py --fy FY26
```

**Update after new PDFs:**
```bash
# Add new PDFs to credit_card_statements/ folder, then:
python extract_cc_statements_to_excel.py --fy FY26

# Regenerate narration with updated CC data
python run_narration.py --fy FY26
```

**Multiple fiscal years:**
```bash
# Setup both FY25 and FY26
python extract_cc_statements_to_excel.py --fy FY25
python extract_cc_statements_to_excel.py --fy FY26

# Use either independently
python run_narration.py --fy FY25
python run_narration.py --fy FY26
```

---

## Troubleshooting

**Cache not being used:**
- Ensure the cache file exists: `e:\Tax\Aayush\Generated Data\FY26\CC_Statements_Cache_FY26.xlsx`
- Check file naming (must include the FY suffix)

**Stale data:**
- Regenerate cache after adding new PDF statements
- Always regenerate before final reconciliation

**Force PDF re-extraction:**
- Delete the cache file
- Re-run narration (will extract from PDFs)
- Or run `extract_cc_statements_to_excel.py` to regenerate

---

## API Reference

### `extract_cc_statements_to_excel.py`

Command-line tool for extraction.

```bash
python extract_cc_statements_to_excel.py --fy FY26
```

**Arguments:**
- `--fy {FY25, FY26}`: Fiscal year (default: FY26)

**Returns:**
- Excel file at `e:\Tax\Aayush\Generated Data\<FY>\CC_Statements_Cache_<FY>.xlsx`

---

### `parse_cc.parse_all_statements_from_cache()`

Python function to load cached CC statements.

```python
from narration_engine.parse_cc import parse_all_statements_from_cache

cache_path = "e:\\Tax\\Aayush\\Generated Data\\FY26\\CC_Statements_Cache_FY26.xlsx"
cc_df, metas = parse_all_statements_from_cache(cache_path)

print(f"Loaded {len(cc_df)} transactions from {len(metas)} statements")
```

**Returns:**
- `cc_df`: DataFrame with columns [TX_Date, Particulars, Merchant, CC_Category, Auto_Narration, Account_Head, DR, CR, Statement_Period, Pay_By, Source]
- `metas`: List of statement metadata dicts

---

## Notes

- Cache format: Excel (.xlsx) with openpyxl engine
- Supports multiple FY ranges (FY25, FY26, etc.)
- All dates in cache are stored as `date` type for cleaner display
- Metadata sheet preserves original PDF paths for reference
