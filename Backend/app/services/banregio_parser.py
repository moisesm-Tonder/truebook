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
    """Extract table data from Banregio PDF bank statement."""
    try:
        import pdfplumber
        rows = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            rows.append(row)
        if not rows:
            return pd.DataFrame()

        # Use first non-empty row as header
        header = rows[0]
        data = rows[1:]
        df = pd.DataFrame(data, columns=header)
        return df
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

    # Try to identify date, description, debit, credit columns
    col_lower = {c.lower(): c for c in df.columns}

    date_col = next((col_lower[k] for k in ["fecha", "date", "f. operacion"] if k in col_lower), df.columns[0] if len(df.columns) > 0 else None)
    desc_col = next((col_lower[k] for k in ["descripcion", "concepto", "description", "referencia"] if k in col_lower), None)
    debit_col = next((col_lower[k] for k in ["cargo", "debito", "debit"] if k in col_lower), None)
    credit_col = next((col_lower[k] for k in ["abono", "credito", "credit", "deposito"] if k in col_lower), None)

    # Column H (index 7) is the deposit reference column per the spec
    deposit_col_name = df.columns[7] if len(df.columns) > 7 else credit_col

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
