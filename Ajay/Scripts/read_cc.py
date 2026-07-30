import pdfplumber, pathlib, re

cc_dir = pathlib.Path(r"E:\Tax\credit_card_statements")
pdfs = sorted(cc_dir.glob("*.pdf"))

print(f"Found {len(pdfs)} PDFs\n")
print("=== Statement periods and totals ===\n")

for pdf_path in pdfs:
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                full_text += t + "\n"

    # Statement date
    stmt_date = re.search(r"StatementDate\s+(\d{2}-\w{3}-\d{4})", full_text)
    # Period
    period = re.search(r"from\s+(\d{2}-\w{3}-\d{4})\s+to\s+(\d{2}-\w{3}-\d{4})", full_text)
    # Pay by
    pay_by  = re.search(r"Remembertopayby\s+(\d{2}-\w{3}-\d{4})", full_text)
    # TAD
    tad     = re.search(r"TotalAmountDue\(TAD\)\s+(Rs\.[\d,]+\.\d{2})", full_text)

    print(f"  Statement: {stmt_date.group(1) if stmt_date else '?'}")
    print(f"  Period   : {period.group(1) if period else '?'} -> {period.group(2) if period else '?'}")
    print(f"  Pay by   : {pay_by.group(1) if pay_by else '?'}")
    print(f"  TAD      : {tad.group(1) if tad else '?'}")
    print()
