"""
Banregio file parser.
Accepts PDF (bank statement) or Excel/CSV.
Produces movements list and summary.
Column H = deposit amount used for Kushki vs Banregio cross-check.
"""
import logging
import io
import re
from typing import Dict, Any, List
import pandas as pd

logger = logging.getLogger(__name__)


def _parse_pdf(content: bytes) -> pd.DataFrame:
    """Extract movement rows from Banregio PDF bank statement using text extraction."""
    try:
        import pdfplumber

        # Regex for a row starting with a date DD/MM/YYYY
        DATE_RE = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.+)$')
        # Regex to find monetary amounts like $ 1,234,567.89 or $1234567.89
        AMOUNT_RE = re.compile(r'\$\s*([\d,]+\.\d{2})')

        rows = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split('\n'):
                    line = line.strip()
                    m = DATE_RE.match(line)
                    if not m:
                        continue
                    date = m.group(1)
                    rest = m.group(2)

                    # Extract all amounts from the line
                    amounts = [float(a.replace(',', '')) for a in AMOUNT_RE.findall(rest)]

                    # Banregio format: ... Cargos  Abonos  Saldo
                    # A line has either a cargo, an abono, or both; saldo is always last
                    cargo = 0.0
                    abono = 0.0

                    if len(amounts) >= 3:
                        # cargo, abono, saldo
                        cargo = amounts[0]
                        abono = amounts[1]
                    elif len(amounts) == 2:
                        # either (cargo, saldo) or (abono, saldo)
                        # Determine by position: look for $ sign occurrences
                        # Use context: if "cargo" text position comes before "abono"
                        # Simpler: check if the line contains patterns that suggest credit
                        rest_clean = rest.upper()
                        is_credit = any(kw in rest_clean for kw in [
                            'PAGO CAP', 'PAGO INT', 'SPEI', 'INVERSION', 'ABONO',
                            'VENTA DE', 'REEMBOLSO', 'BNET', 'NVIO', 'BANKAOOL',
                            'FINCO PAY'
                        ])
                        if is_credit:
                            abono = amounts[0]
                        else:
                            cargo = amounts[0]
                    elif len(amounts) == 1:
                        # Only saldo — skip
                        continue

                    # Strip description: remove amounts from rest
                    desc = AMOUNT_RE.sub('', rest).strip()
                    # Remove trailing/leading underscores and references
                    desc = re.sub(r'\s{2,}', ' ', desc).strip()

                    rows.append({
                        'Fecha': date,
                        'Descripcion': desc,
                        'Cargos': cargo,
                        'Abonos': abono,
                    })

        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)

    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        return pd.DataFrame()


def _parse_structured(content: bytes, filename: str) -> pd.DataFrame:
    fname = filename.lower()
    if fname.endswith(".csv"):
        try:
            return pd.read_csv(io.BytesIO(content), encoding="utf-8")
        except Exception:
            return pd.read_csv(io.BytesIO(content), encoding="latin-1")
    elif fname.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(content))
    return pd.DataFrame()


def _clean_amount(val) -> float:
    if val is None:
        return 0.0
    s = str(val).replace(",", "").replace("$", "").strip()
    try:
        return float(s)
    except Exception:
        return 0.0


def parse_banregio(content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse Banregio bank statement.
    Column H (index 7) = deposit amount for cross-check with Kushki col I.
    """
    fname = filename.lower()
    if fname.endswith(".pdf"):
        df = _parse_pdf(content)
    else:
        df = _parse_structured(content, filename)

    if df.empty:
        return {"movements": [], "summary": {}, "deposit_column": [], "row_count": 0}

    # Normalize columns
    df.columns = [str(c).strip() for c in df.columns]
    col_lower = {c.lower(): c for c in df.columns}

    date_col  = next((col_lower[k] for k in ["fecha", "date", "f. operacion"] if k in col_lower), df.columns[0])
    desc_col  = next((col_lower[k] for k in ["descripcion", "concepto", "description", "referencia"] if k in col_lower), None)
    debit_col = next((col_lower[k] for k in ["cargos", "cargo", "debito", "debit"] if k in col_lower), None)
    credit_col= next((col_lower[k] for k in ["abonos", "abono", "credito", "credit", "deposito"] if k in col_lower), None)
    deposit_col_name = credit_col  # For Banregio the abono IS the deposit ref

    movements = []
    for _, row in df.iterrows():
        mv = {
            "date": str(row[date_col]) if date_col and date_col in row.index else "",
            "description": str(row[desc_col]) if desc_col and desc_col in row.index else "",
            "debit": _clean_amount(row[debit_col]) if debit_col and debit_col in row.index else 0.0,
            "credit": _clean_amount(row[credit_col]) if credit_col and credit_col in row.index else 0.0,
            "deposit_ref": _clean_amount(row[deposit_col_name]) if deposit_col_name and deposit_col_name in row.index else 0.0,
        }
        movements.append(mv)

    total_credits = sum(m["credit"] for m in movements)
    total_debits = sum(m["debit"] for m in movements)
    deposit_refs = [m["deposit_ref"] for m in movements if m["deposit_ref"] > 0]

    summary = {
        "total_credits": round(total_credits, 6),
        "total_debits": round(total_debits, 6),
        "net": round(total_credits - total_debits, 6),
        "deposit_count": len(deposit_refs),
        "total_deposit_ref": round(sum(deposit_refs), 6),
    }

    return {
        "movements": movements,
        "summary": summary,
        "deposit_column": deposit_refs,  # Column H values for cross-check
        "row_count": len(movements),
    }
