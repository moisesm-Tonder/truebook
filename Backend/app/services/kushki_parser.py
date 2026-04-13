"""
Kushki file parser.
Supports:
- Consolidated files (CSV/Excel) with daily and merchant summaries.
- Raw daily files from SFTP (sheet "Resumen" with headers after intro rows).
"""
import io
import logging
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

MERCHANT_EXACT_ALIASES = {
    "afun": "Afun Mexico",
    "vitau medical": "Vitau",
    "alamo ent viva mex": "Viva Mex",
    "alamo vivento 4 rios": "Vivento 4 Rios",
    "alamo el dorado": "El Dorado",
    "strendus vip": "Strendus",
    "strendus": "Strendus",
    "ent hollywood valle alto": "Hollywood Valle Alto",
}

MERCHANT_PREFIX_ALIASES = {
    "bexar ": "",
    "obsidiana ": "",
    "onix ": "",
}

# Expected column variants (normalized) -> canonical name
COLUMN_MAP = {
    "fecha": "date",
    "date": "date",
    "fecha liq": "date",
    "fecha liq.": "date",
    "fecha pago": "date",
    "fecha de pago": "date",
    "merchant": "merchant_name",
    "comercio": "merchant_name",
    "merchant name": "merchant_name",
    "merchant_name": "merchant_name",
    "transaction_status": "transaction_status",
    "status": "transaction_status",
    "estado transaccion": "transaction_status",
    "estatus transaccion": "transaction_status",
    "transacciones": "tx_count",
    "transactions": "tx_count",
    "# txns": "tx_count",
    "txns": "tx_count",
    "cuenta de ticket_number": "tx_count",
    "cuenta de ticket number": "tx_count",
    "monto bruto": "gross_amount",
    "gross": "gross_amount",
    "gross_amount": "gross_amount",
    "suma de approved_transaction_amount": "gross_amount",
    "comision": "commission",
    "comision kushki": "kushki_commission",
    "comision kushki s/iva": "kushki_commission",
    "comision kushki + iva": "commission",
    "com. kushki + iva": "commission",
    "com. kushki": "kushki_commission",
    "commission": "commission",
    "fee": "commission",
    "suma de kushki_commission": "kushki_commission",
    "suma de iva_kushki_commission": "iva_kushki_commission",
    "iva kushki": "iva_kushki_commission",
    "rolling reserve": "rr_retained",
    "rolling_reserve": "rr_retained",
    "rr retenido": "rr_retained",
    "suma de fraud_retention": "rr_retained",
    "rr liberado": "rr_released",
    "suma de liberacion de fondos": "rr_released",
    "com tonder s/iva": "tonder_commission",
    "comision tonder": "tonder_commission",
    "comision tonder s/iva": "tonder_commission",
    "com. tonder s/iva": "tonder_commission",
    "com. tonder %": "tonder_commission",
    "tonder_commission": "tonder_commission",
    "ajustes": "adjustments",
    "suma de ajuste": "adjustments",
    "deposito neto": "net_deposit",
    "deposito neto merchant": "net_deposit",
    "net deposit": "net_deposit",
    "net_deposit": "net_deposit",
    "deposito neto (abonar)": "net_deposit",
    "monto abonar": "net_deposit",
    "suma de monto abonar": "net_deposit",
}


def _norm_text(value: Any) -> str:
    s = str(value or "").strip().lower().replace("\n", " ")
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    s = " ".join(s.split())
    return s


def _title_words(value: str) -> str:
    parts = [p for p in str(value).split(" ") if p]
    return " ".join(p[:1].upper() + p[1:] for p in parts)


def _canonical_merchant_name(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""

    normalized = _norm_text(raw)
    if not normalized:
        return ""

    if normalized in MERCHANT_EXACT_ALIASES:
        return MERCHANT_EXACT_ALIASES[normalized]

    for prefix, replacement in MERCHANT_PREFIX_ALIASES.items():
        if normalized.startswith(prefix):
            normalized = (replacement + normalized[len(prefix):]).strip()
            break

    if normalized in MERCHANT_EXACT_ALIASES:
        return MERCHANT_EXACT_ALIASES[normalized]

    if normalized != _norm_text(raw):
        return _title_words(normalized)

    return raw


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for col in df.columns:
        normalized = _norm_text(col)
        canonical = COLUMN_MAP.get(normalized)
        rename[col] = canonical if canonical else normalized
    return df.rename(columns=rename)


def _normalize_date(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    s = str(value).strip()
    if not s or s.lower() in {"none", "nan"}:
        return ""

    try:
        n = float(s)
        if 30000 <= n <= 60000:
            return (datetime(1899, 12, 30) + timedelta(days=int(n))).date().isoformat()
    except Exception:
        pass

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date().isoformat()
        except Exception:
            continue

    parsed = pd.to_datetime(s, errors="coerce")
    if pd.notna(parsed):
        return parsed.date().isoformat()

    return s[:10]


def _is_iso_date(value: Any) -> bool:
    s = str(value or "").strip()
    if len(s) != 10:
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except Exception:
        return False


def _find_header_row(raw: pd.DataFrame, max_scan_rows: int = 35) -> Optional[int]:
    scan = min(len(raw.index), max_scan_rows)
    for i in range(scan):
        row_values = [_norm_text(v) for v in raw.iloc[i].tolist() if str(v).strip() not in ("", "None", "nan")]
        if not row_values:
            continue
        joined = " | ".join(row_values)
        has_date = any(x in row_values for x in ("fecha de pago", "fecha liq.", "fecha liq", "fecha", "date"))
        has_amount = (
            "suma de monto abonar" in joined
            or "monto abonar" in joined
            or "deposito neto (abonar)" in joined
            or "net_deposit" in joined
            or "monto bruto" in joined
        )
        if has_date and has_amount:
            return i
    return None


def _parse_excel(content: bytes) -> pd.DataFrame:
    xls = pd.ExcelFile(io.BytesIO(content))
    preferred = ["Resumen Diario", "Resumen", "Detalle por Merchant", "Detalle de Liquidacion"]
    sheets = [s for s in preferred if s in xls.sheet_names] + [s for s in xls.sheet_names if s not in preferred]

    best_df = None
    best_score = -1
    for sheet in sheets:
        try:
            raw = pd.read_excel(io.BytesIO(content), sheet_name=sheet, header=None)
        except Exception:
            continue

        header_row = _find_header_row(raw)
        if header_row is None:
            header_row = 0

        try:
            df = pd.read_excel(io.BytesIO(content), sheet_name=sheet, header=header_row)
        except Exception:
            continue

        df = _normalize_columns(df)
        score = 0
        for col in ("date", "net_deposit", "gross_amount", "merchant_name", "tx_count"):
            if col in df.columns:
                score += 1

        if score > best_score:
            best_score = score
            best_df = df

        if score >= 3:
            return df

    if best_df is not None:
        return best_df
    raise ValueError("Unable to identify a valid Kushki sheet")


def _parse_file(content: bytes, filename: str) -> pd.DataFrame:
    fname = filename.lower()
    if fname.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8")
        except Exception:
            df = pd.read_csv(io.BytesIO(content), encoding="latin-1")
        return _normalize_columns(df)
    if fname.endswith((".xlsx", ".xls")):
        return _parse_excel(content)
    raise ValueError(f"Unsupported file type: {filename}")


def _read_excel_sheet(content: bytes, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(io.BytesIO(content), sheet_name=sheet_name, header=None)
    header_row = _find_header_row(raw)
    if header_row is None:
        header_row = 0
    df = pd.read_excel(io.BytesIO(content), sheet_name=sheet_name, header=header_row)
    return _normalize_columns(df)


def _prepare_kushki_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    had_rr_retained = "rr_retained" in df.columns
    had_rr_released = "rr_released" in df.columns

    defaults = {
        "date": "",
        "merchant_name": "",
        "transaction_status": "",
        "tx_count": 0.0,
        "gross_amount": 0.0,
        "commission": 0.0,
        "kushki_commission": 0.0,
        "iva_kushki_commission": 0.0,
        "rr_retained": 0.0,
        "rr_released": 0.0,
        "tonder_commission": 0.0,
        "adjustments": 0.0,
        "net_deposit": 0.0,
    }
    for col, default_value in defaults.items():
        if col not in df.columns:
            df[col] = default_value

    # Backward compatibility for older exports that only had rolling_reserve.
    if "rolling_reserve" in df.columns:
        roll = pd.to_numeric(df.get("rolling_reserve", 0), errors="coerce").fillna(0.0)
        rr_retained_current = pd.to_numeric(df.get("rr_retained", 0), errors="coerce").fillna(0.0)
        rr_released_current = pd.to_numeric(df.get("rr_released", 0), errors="coerce").fillna(0.0)
        if (not had_rr_retained) or rr_retained_current.abs().sum() == 0:
            df["rr_retained"] = roll.clip(lower=0)
        if (not had_rr_released) or rr_released_current.abs().sum() == 0:
            df["rr_released"] = (-roll).clip(lower=0)

    # Keep commission split explicit (commission without IVA + IVA), and derive total when needed.
    commission = pd.to_numeric(df.get("commission", 0), errors="coerce").fillna(0.0)
    kushki_comm = pd.to_numeric(df.get("kushki_commission", 0), errors="coerce").fillna(0.0)
    iva_comm = pd.to_numeric(df.get("iva_kushki_commission", 0), errors="coerce").fillna(0.0)

    if commission.abs().sum() == 0:
        commission = kushki_comm + iva_comm

    missing_kushki_comm = kushki_comm == 0
    derived_kushki_comm = (commission - iva_comm).where(iva_comm != 0, commission / 1.16)
    kushki_comm = kushki_comm.where(~missing_kushki_comm, derived_kushki_comm)

    missing_iva = iva_comm == 0
    derived_iva = (commission - kushki_comm).clip(lower=0)
    iva_comm = iva_comm.where(~missing_iva, derived_iva)

    df["commission"] = commission
    df["kushki_commission"] = kushki_comm
    df["iva_kushki_commission"] = iva_comm

    numeric_cols = [
        "tx_count",
        "gross_amount",
        "commission",
        "kushki_commission",
        "iva_kushki_commission",
        "rr_retained",
        "rr_released",
        "tonder_commission",
        "adjustments",
        "net_deposit",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["date"] = df["date"].map(_normalize_date)
    df["merchant_name"] = df["merchant_name"].map(_canonical_merchant_name)
    df["transaction_status"] = df["transaction_status"].astype(str).str.strip()
    df = df[df["date"].map(_is_iso_date)].copy()
    return df


def parse_kushki(content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse one Kushki file.
    Returns daily_summary and merchant_detail.
    """
    df = _prepare_kushki_df(_parse_file(content, filename))
    if df.empty:
        return {
            "daily_summary": [],
            "merchant_detail": [],
            "total_net_deposit": 0.0,
            "row_count": 0,
        }

    # TONDER rows represent released rolling reserve and should not show in merchant detail.
    merchant_norm = df["merchant_name"].map(_norm_text)
    is_tonder = merchant_norm == "tonder"
    tonder_release = is_tonder.astype(float) * df["net_deposit"]
    # Some source files already include RR liberado; only fallback to TONDER net when RR is missing.
    df["rr_released_total"] = df["rr_released"].where(df["rr_released"] != 0, tonder_release)
    df["rolling_reserve"] = df["rr_retained"] - df["rr_released_total"]

    daily = (
        df.groupby("date", as_index=False)
        .agg(
            tx_count=("tx_count", "sum"),
            gross_amount=("gross_amount", "sum"),
            commission=("commission", "sum"),
            kushki_commission=("kushki_commission", "sum"),
            iva_kushki_commission=("iva_kushki_commission", "sum"),
            rr_retained=("rr_retained", "sum"),
            rr_released=("rr_released_total", "sum"),
            tonder_commission=("tonder_commission", "sum"),
            adjustments=("adjustments", "sum"),
            rolling_reserve=("rolling_reserve", "sum"),
            net_deposit=("net_deposit", "sum"),
        )
    )

    daily_summary = []
    for _, row in daily.sort_values(by=["date"]).iterrows():
        daily_summary.append({
            "date": row["date"],
            "tx_count": int(round(float(row["tx_count"]), 0)),
            "gross_amount": round(float(row["gross_amount"]), 6),
            "commission": round(float(row["commission"]), 6),
            "kushki_commission": round(float(row["kushki_commission"]), 6),
            "iva_kushki_commission": round(float(row["iva_kushki_commission"]), 6),
            "rr_retained": round(float(row["rr_retained"]), 6),
            "rr_released": round(float(row["rr_released"]), 6),
            "tonder_commission": round(float(row["tonder_commission"]), 6),
            "adjustments": round(float(row["adjustments"]), 6),
            "rolling_reserve": round(float(row["rolling_reserve"]), 6),
            "net_deposit": round(float(row["net_deposit"]), 6),
        })

    merchant_source = df[~is_tonder].copy()

    # When source file already contains "Detalle por Merchant", prefer it to preserve
    # merchant granularity (including day+merchant rows when available).
    fname = filename.lower()
    if fname.endswith((".xlsx", ".xls")):
        try:
            xls = pd.ExcelFile(io.BytesIO(content))
            if "Detalle por Merchant" in xls.sheet_names:
                detail_df = _prepare_kushki_df(_read_excel_sheet(content, "Detalle por Merchant"))
                if not detail_df.empty and detail_df["merchant_name"].astype(str).str.strip().ne("").any():
                    detail_norm = detail_df["merchant_name"].map(_norm_text)
                    detail_is_tonder = detail_norm == "tonder"
                    detail_tonder_release = detail_is_tonder.astype(float) * detail_df["net_deposit"]
                    detail_df["rr_released_total"] = detail_df["rr_released"].where(
                        detail_df["rr_released"] != 0, detail_tonder_release
                    )
                    detail_df["rolling_reserve"] = detail_df["rr_retained"] - detail_df["rr_released_total"]
                    merchant_source = detail_df[~detail_is_tonder].copy()
        except Exception as exc:
            logger.warning(f"Unable to parse Detalle por Merchant sheet from {filename}: {exc}")

    merchant_detail: List[Dict[str, Any]] = []
    if not merchant_source.empty:
        merchant = (
            merchant_source.groupby(["date", "merchant_name"], as_index=False)
            .agg(
                tx_count=("tx_count", "sum"),
                gross_amount=("gross_amount", "sum"),
                commission=("commission", "sum"),
                kushki_commission=("kushki_commission", "sum"),
                iva_kushki_commission=("iva_kushki_commission", "sum"),
                rr_retained=("rr_retained", "sum"),
                rr_released=("rr_released_total", "sum"),
                tonder_commission=("tonder_commission", "sum"),
                rolling_reserve=("rolling_reserve", "sum"),
                net_deposit=("net_deposit", "sum"),
            )
        )
        for _, row in merchant.sort_values(by=["date", "merchant_name"]).iterrows():
            merchant_detail.append({
                "date": row["date"],
                "merchant_name": str(row["merchant_name"]).strip() or "unknown",
                "tx_count": int(round(float(row["tx_count"]), 0)),
                "gross_amount": round(float(row["gross_amount"]), 6),
                "commission": round(float(row["commission"]), 6),
                "kushki_commission": round(float(row["kushki_commission"]), 6),
                "iva_kushki_commission": round(float(row["iva_kushki_commission"]), 6),
                "rr_retained": round(float(row["rr_retained"]), 6),
                "rr_released": round(float(row["rr_released"]), 6),
                "tonder_commission": round(float(row["tonder_commission"]), 6),
                "rolling_reserve": round(float(row["rolling_reserve"]), 6),
                "net_deposit": round(float(row["net_deposit"]), 6),
            })

    total_net = round(sum(r["net_deposit"] for r in daily_summary), 6)
    return {
        "daily_summary": daily_summary,
        "merchant_detail": merchant_detail,
        "total_net_deposit": total_net,
        "row_count": len(df),
    }


def merge_kushki_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Consolidate multiple Kushki parsed outputs into a single clean monthly dataset.
    This avoids duplicated rows when the month arrives split across many files.
    """
    daily_acc = defaultdict(lambda: {
        "tx_count": 0.0,
        "gross_amount": 0.0,
        "commission": 0.0,
        "kushki_commission": 0.0,
        "iva_kushki_commission": 0.0,
        "rr_retained": 0.0,
        "rr_released": 0.0,
        "tonder_commission": 0.0,
        "adjustments": 0.0,
        "rolling_reserve": 0.0,
        "net_deposit": 0.0,
    })
    merchant_acc = defaultdict(lambda: {
        "tx_count": 0.0,
        "gross_amount": 0.0,
        "commission": 0.0,
        "kushki_commission": 0.0,
        "iva_kushki_commission": 0.0,
        "rr_retained": 0.0,
        "rr_released": 0.0,
        "tonder_commission": 0.0,
        "rolling_reserve": 0.0,
        "net_deposit": 0.0,
    })

    for result in results:
        for row in result.get("daily_summary", []) or []:
            day = str(row.get("date", "")).strip()
            if not day:
                continue
            daily_acc[day]["tx_count"] += float(row.get("tx_count", 0) or 0)
            daily_acc[day]["gross_amount"] += float(row.get("gross_amount", 0) or 0)
            daily_acc[day]["commission"] += float(row.get("commission", 0) or 0)
            daily_acc[day]["kushki_commission"] += float(row.get("kushki_commission", 0) or 0)
            daily_acc[day]["iva_kushki_commission"] += float(row.get("iva_kushki_commission", 0) or 0)
            daily_acc[day]["rr_retained"] += float(row.get("rr_retained", 0) or 0)
            daily_acc[day]["rr_released"] += float(row.get("rr_released", 0) or 0)
            daily_acc[day]["tonder_commission"] += float(row.get("tonder_commission", 0) or 0)
            daily_acc[day]["adjustments"] += float(row.get("adjustments", 0) or 0)
            daily_acc[day]["rolling_reserve"] += float(row.get("rolling_reserve", 0) or 0)
            daily_acc[day]["net_deposit"] += float(row.get("net_deposit", 0) or 0)

        for row in result.get("merchant_detail", []) or []:
            day = str(row.get("date", "")).strip()
            merchant = _canonical_merchant_name(row.get("merchant_name", "unknown")) or "unknown"
            if not day:
                continue
            key = (day, merchant)
            merchant_acc[key]["tx_count"] += float(row.get("tx_count", 0) or 0)
            merchant_acc[key]["gross_amount"] += float(row.get("gross_amount", 0) or 0)
            merchant_acc[key]["commission"] += float(row.get("commission", 0) or 0)
            merchant_acc[key]["kushki_commission"] += float(row.get("kushki_commission", 0) or 0)
            merchant_acc[key]["iva_kushki_commission"] += float(row.get("iva_kushki_commission", 0) or 0)
            merchant_acc[key]["rr_retained"] += float(row.get("rr_retained", 0) or 0)
            merchant_acc[key]["rr_released"] += float(row.get("rr_released", 0) or 0)
            merchant_acc[key]["tonder_commission"] += float(row.get("tonder_commission", 0) or 0)
            merchant_acc[key]["rolling_reserve"] += float(row.get("rolling_reserve", 0) or 0)
            merchant_acc[key]["net_deposit"] += float(row.get("net_deposit", 0) or 0)

    daily_summary = []
    for day, data in sorted(daily_acc.items(), key=lambda x: x[0]):
        daily_summary.append({
            "date": day,
            "tx_count": int(round(data["tx_count"], 0)),
            "gross_amount": round(data["gross_amount"], 6),
            "commission": round(data["commission"], 6),
            "kushki_commission": round(data["kushki_commission"], 6),
            "iva_kushki_commission": round(data["iva_kushki_commission"], 6),
            "rr_retained": round(data["rr_retained"], 6),
            "rr_released": round(data["rr_released"], 6),
            "tonder_commission": round(data["tonder_commission"], 6),
            "adjustments": round(data["adjustments"], 6),
            "rolling_reserve": round(data["rolling_reserve"], 6),
            "net_deposit": round(data["net_deposit"], 6),
        })

    merchant_detail = []
    for (day, merchant), data in sorted(merchant_acc.items(), key=lambda x: (x[0][0], x[0][1].lower())):
        merchant_detail.append({
            "date": day,
            "merchant_name": merchant,
            "tx_count": int(round(data["tx_count"], 0)),
            "gross_amount": round(data["gross_amount"], 6),
            "commission": round(data["commission"], 6),
            "kushki_commission": round(data["kushki_commission"], 6),
            "iva_kushki_commission": round(data["iva_kushki_commission"], 6),
            "rr_retained": round(data["rr_retained"], 6),
            "rr_released": round(data["rr_released"], 6),
            "tonder_commission": round(data["tonder_commission"], 6),
            "rolling_reserve": round(data["rolling_reserve"], 6),
            "net_deposit": round(data["net_deposit"], 6),
        })

    total_net = round(sum(r["net_deposit"] for r in daily_summary), 6)
    return {
        "daily_summary": daily_summary,
        "merchant_detail": merchant_detail,
        "total_net_deposit": total_net,
    }
