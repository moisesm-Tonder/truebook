"""
Banregio file parser.
Accepts PDF (bank statement) or Excel/CSV.
Produces movements list and summary.
Column H (or equivalent) is used as deposit reference for Kushki cross-check.
"""

import io
import logging
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)


def _parse_pdf(content: bytes) -> pd.DataFrame:
    """Extract movement rows from Banregio PDF bank statement using text extraction."""
    try:
        import pdfplumber

        date_re = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.+)$")
        amount_re = re.compile(r"\$\s*([\d,]+\.\d{2})")

        rows = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split("\n"):
                    line = line.strip()
                    match = date_re.match(line)
                    if not match:
                        continue
                    movement_date = match.group(1)
                    rest = match.group(2)
                    amounts = [float(a.replace(",", "")) for a in amount_re.findall(rest)]

                    debit = 0.0
                    credit = 0.0
                    if len(amounts) >= 3:
                        debit = amounts[0]
                        credit = amounts[1]
                    elif len(amounts) == 2:
                        rest_clean = rest.upper()
                        is_credit = any(
                            kw in rest_clean
                            for kw in [
                                "PAGO CAP",
                                "PAGO INT",
                                "SPEI",
                                "INVERSION",
                                "ABONO",
                                "VENTA DE",
                                "REEMBOLSO",
                                "BNET",
                                "NVIO",
                                "BANKAOOL",
                                "FINCO PAY",
                            ]
                        )
                        if is_credit:
                            credit = amounts[0]
                        else:
                            debit = amounts[0]
                    elif len(amounts) == 1:
                        continue

                    description = amount_re.sub("", rest).strip()
                    description = re.sub(r"\s{2,}", " ", description).strip()
                    rows.append(
                        {
                            "Fecha": movement_date,
                            "Descripcion": description,
                            "Cargos": debit,
                            "Abonos": credit,
                        }
                    )

        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception as exc:
        logger.error(f"PDF parse error: {exc}")
        return pd.DataFrame()


def _parse_structured(content: bytes, filename: str) -> pd.DataFrame:
    fname = filename.lower()
    if fname.endswith(".csv"):
        try:
            return pd.read_csv(io.BytesIO(content), encoding="utf-8")
        except Exception:
            return pd.read_csv(io.BytesIO(content), encoding="latin-1")
    if fname.endswith((".xlsx", ".xls")):
        xls = pd.ExcelFile(io.BytesIO(content))
        preferred = ["MOVIMIENTOS", "Movimientos", "ESTADO DE CUENTA", "Estado de cuenta"]
        sheet_order = [s for s in preferred if s in xls.sheet_names] + [s for s in xls.sheet_names if s not in preferred]

        best_df = None
        best_score = -1
        for sheet in sheet_order:
            try:
                raw = pd.read_excel(io.BytesIO(content), sheet_name=sheet, header=None)
            except Exception:
                continue

            header_row = _find_header_row(raw)
            try:
                df = pd.read_excel(io.BytesIO(content), sheet_name=sheet, header=header_row if header_row is not None else 0)
            except Exception:
                continue

            score = _score_columns(df.columns)
            if score > best_score:
                best_score = score
                best_df = df
            if score >= 3:
                return df

        if best_df is not None:
            return best_df
        return pd.DataFrame()
    return pd.DataFrame()


def _norm_text(value: Any) -> str:
    s = str(value or "").strip().lower().replace("\n", " ")
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def _find_header_row(raw: pd.DataFrame, max_scan_rows: int = 30) -> int | None:
    scan = min(len(raw.index), max_scan_rows)
    for i in range(scan):
        values = [_norm_text(v) for v in raw.iloc[i].tolist() if str(v).strip() not in ("", "None", "nan")]
        if not values:
            continue
        has_date = any(v == "fecha" or v.startswith("fecha ") or "f operacion" in v for v in values)
        has_credit = any("abono" in v or "credito" in v or "deposito" in v for v in values)
        has_debit = any("cargo" in v or "debito" in v for v in values)
        has_desc = any("concepto" in v or "descripcion" in v or "contraparte" in v for v in values)
        if has_date and (has_credit or has_debit or has_desc):
            return i
    return None


def _score_columns(columns) -> int:
    names = {_norm_text(c) for c in columns}
    score = 0
    if any("fecha" in n for n in names):
        score += 1
    if any("abono" in n or "credito" in n for n in names):
        score += 1
    if any("cargo" in n or "debito" in n for n in names):
        score += 1
    if any("concepto" in n or "descripcion" in n for n in names):
        score += 1
    return score


def _normalize_date(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, date):
        return val.isoformat()

    raw = str(val).strip()
    if not raw or raw.lower() in {"nan", "none"}:
        return ""

    try:
        num = float(raw)
        if 30000 <= num <= 60000:
            return (datetime(1899, 12, 30) + timedelta(days=int(num))).date().isoformat()
    except Exception:
        pass

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date().isoformat()
        except Exception:
            continue

    parsed = pd.to_datetime(raw, errors="coerce")
    if pd.notna(parsed):
        return parsed.date().isoformat()
    return raw[:10]


def _clean_amount(val: Any) -> float:
    if val is None:
        return 0.0

    s = str(val).strip()
    if not s or s.lower() in {"none", "nan"}:
        return 0.0

    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    if s.startswith("-"):
        negative = True
        s = s[1:]

    s = s.replace("$", "").replace(" ", "")
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s:
        return 0.0

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s and "." not in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[-1]) in (1, 2):
            s = ".".join(parts)
        else:
            s = "".join(parts)

    try:
        amount = float(s)
        return -amount if negative else amount
    except Exception:
        return 0.0


def parse_banregio(content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse Banregio bank statement.
    """
    fname = filename.lower()
    if fname.endswith(".pdf"):
        df = _parse_pdf(content)
    else:
        df = _parse_structured(content, filename)

    if df.empty:
        return {"movements": [], "summary": {}, "deposit_column": [], "row_count": 0}

    df.columns = [str(c).strip() for c in df.columns]
    col_norm = {_norm_text(c): c for c in df.columns}

    def pick_col(aliases):
        for alias in aliases:
            if alias in col_norm:
                return col_norm[alias]
        for norm_name, original in col_norm.items():
            if any(alias in norm_name for alias in aliases):
                return original
        return None

    date_col = pick_col(["fecha", "date", "f operacion", "fecha operacion"]) or df.columns[0]
    desc_col = pick_col(["descripcion", "concepto", "description", "referencia", "concepto contraparte"])
    type_col = pick_col(["tipo", "type"])
    category_col = pick_col(["categoria", "category"])
    debit_col = pick_col(["cargos", "cargo", "debito", "debit", "egreso"])
    credit_col = pick_col(["abonos", "abono", "credito", "credit", "deposito"])
    deposit_col_name = pick_col(
        [
            "ref deposito",
            "deposit ref",
            "abono banregio",
            "deposito banregio",
            "importe deposito",
        ]
    ) or credit_col

    movements = []
    for _, row in df.iterrows():
        movement_date = _normalize_date(row[date_col]) if date_col and date_col in row.index else ""
        description = str(row[desc_col]).strip() if desc_col and desc_col in row.index else ""
        debit = _clean_amount(row[debit_col]) if debit_col and debit_col in row.index else 0.0
        credit = _clean_amount(row[credit_col]) if credit_col and credit_col in row.index else 0.0
        deposit_ref = _clean_amount(row[deposit_col_name]) if deposit_col_name and deposit_col_name in row.index else 0.0

        if not movement_date and not description and debit == 0 and credit == 0 and deposit_ref == 0:
            continue

        movements.append(
            {
                "date": movement_date,
                "description": description,
                "type": str(row[type_col]).strip() if type_col and type_col in row.index else "",
                "category": str(row[category_col]).strip() if category_col and category_col in row.index else "",
                "debit": debit,
                "credit": credit,
                "deposit_ref": deposit_ref,
            }
        )

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
        "deposit_column": deposit_refs,
        "row_count": len(movements),
    }
