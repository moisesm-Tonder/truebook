"""
Kushki file parser.
Supports:
- Raw Kushki settlements (sheet "Detalle de Liquidacion") with transaction-level logic.
- Backward-compatible summarized files (CSV/Excel) from older exports.
"""
import io
import logging
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

logger = logging.getLogger(__name__)

_INTERNAL_MERCHANTS = {"tonder", "ghost tonder"}

# Kushki -> FEES merchant mapping documented for Jan-Mar 2026.
# Unknown merchants default to fee=0 unless there is an exact FEES merchant match.
KUSHKI_TO_FEES_MAP = {
    "afun": "Afun Mexico",
    "afun vip": "AFUNVIP",
    "alamo": "",
    "alamo el dorado": "El Dorado",
    "alamo ent viva mex": "Viva Mex",
    "alamo vivento 4 rios": "Vivento 4 Rios",
    "bc game": "BCGAME",
    "betcris": "Betcris",
    "betcris vip": "Betcris VIP",
    "betxico": "",
    "bexar": "__BEXAR_GENERIC__",
    "bexar ent hollywood valle alto": "Hollywood Valle Alto",
    "bexar grand leon": "Grand Leon",
    "bexar hollywood const": "Hollywood Const",
    "bexar newyork": "NewYork",
    "big bola": "Big Bola",
    "branzino 777": "Brazino 777",
    "coqueteos cercanos": "Artilu MX",
    "estadio gana": "Estadio Gana",
    "gangabet": "Kashio",
    "ghost tonder": "",
    "hard rock": "Hard Rock",
    "idem club": "Idem Club",
    "obsidiana ent jubilee grand c": "Jubilee Grand Casino",
    "obsidiana golden island": "Golden Island",
    "obsidianda": "Diamante",
    "onix jubilee cancun": "Jubilee Cancun",
    "onix tajmahal": "Tajmahal",
    "onix vivento zapopan": "",
    "pesix": "CampoBet",
    "rsn": "elevo",
    "stadiobet": "Stadiobet",
    "strendus": "Strendus",
    "strendus vip": "Strendus VIP",
    "tonder": "Tonder Production",
    "vitau medical": "Vitau",
}

MERCHANT_EXACT_ALIASES = {
    "afun": "AFUN",
    "afun vip": "AFUN VIP",
    "vitau medical": "VITAU MEDICAL",
    "alamo ent viva mex": "ALAMO ENT VIVA MEX",
    "alamo vivento 4 rios": "ALAMO VIVENTO 4 RIOS",
    "alamo el dorado": "ALAMO EL DORADO",
    "strendus vip": "STRENDUS VIP",
    "strendus": "STRENDUS",
    "ent hollywood valle alto": "ENT HOLLYWOOD VALLE ALTO",
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
    "transaction_type": "transaction_type",
    "tipo de transaccion": "transaction_type",
    "tipo transaccion": "transaction_type",
    "transacciones": "tx_count",
    "transactions": "tx_count",
    "# txns": "tx_count",
    "txns": "tx_count",
    "cuenta de ticket_number": "tx_count",
    "cuenta de ticket number": "tx_count",
    "monto bruto": "gross_amount",
    "gross": "gross_amount",
    "gross_amount": "gross_amount",
    "approved_transaction_amount": "approved_amount",
    "approved transaction amount": "approved_amount",
    "suma de approved_transaction_amount": "approved_amount",
    "comision": "commission",
    "comision kushki": "kushki_commission",
    "comision kushki s/iva": "kushki_commission",
    "comision kushki + iva": "commission",
    "com. kushki + iva": "commission",
    "com. kushki": "kushki_commission",
    "commission": "commission",
    "fee": "commission",
    "kushki_commission": "kushki_commission",
    "suma de kushki_commission": "kushki_commission",
    "iva_kushki_commission": "iva_kushki_commission",
    "suma de iva_kushki_commission": "iva_kushki_commission",
    "iva kushki": "iva_kushki_commission",
    "fraud_retention": "rr_retained",
    "rolling reserve": "rr_retained",
    "rolling_reserve": "rr_retained",
    "rr retenido": "rr_retained",
    "suma de fraud_retention": "rr_retained",
    "liberacion de fondos": "rr_released",
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

RAW_DETAIL_POSITION_MAP = {
    "date": 0,
    "merchant_name": 6,
    "transaction_status": 10,
    "transaction_type": 17,
    "approved_amount": 29,
    "kushki_commission": 37,
    "iva_kushki_commission": 38,
    "rr_retained": 41,
    "rr_released": 44,
    "net_deposit": 47,
}

DAILY_NUMERIC_FIELDS = [
    "tx_count",
    "gross_amount",
    "gross_adjustments",
    "commission",
    "kushki_commission",
    "iva_kushki_commission",
    "rr_retained",
    "rr_released",
    "tonder_commission",
    "tonder_iva",
    "tonder_total",
    "refund",
    "chargeback",
    "void",
    "manual",
    "adjustments",
    "rolling_reserve",
    "net_deposit",
    "net_verification",
    "validation_diff",
]

MERCHANT_NUMERIC_FIELDS = [
    "tx_count",
    "gross_amount",
    "gross_adjustments",
    "commission",
    "kushki_commission",
    "iva_kushki_commission",
    "rr_retained",
    "rr_released",
    "tonder_commission",
    "tonder_iva",
    "tonder_total",
    "refund",
    "chargeback",
    "void",
    "manual",
    "adjustments",
    "rolling_reserve",
    "net_deposit",
    "net_verification",
    "validation_diff",
]


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
    preferred = ["Detalle de Liquidacion", "Resumen Diario", "Resumen", "Detalle por Merchant"]
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
        for col in ("date", "net_deposit", "merchant_name", "transaction_type", "approved_amount"):
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


def _extract_filename_settlement_date(filename: str) -> str:
    m = re.search(r"tonder_(\d{4}-\d{2}-\d{2})", str(filename or ""), flags=re.IGNORECASE)
    if not m:
        return ""
    value = _normalize_date(m.group(1))
    return value if _is_iso_date(value) else ""


def _is_internal_merchant(merchant_name: Any) -> bool:
    return _norm_text(merchant_name) in _INTERNAL_MERCHANTS


def _to_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _series_from_candidates(
    df: pd.DataFrame,
    names: Sequence[str],
    fallback_idx: Optional[int] = None,
) -> pd.Series:
    for name in names:
        if name in df.columns:
            return df[name]
    if fallback_idx is not None and 0 <= fallback_idx < len(df.columns):
        return df.iloc[:, fallback_idx]
    return pd.Series([None] * len(df), index=df.index)


def _is_raw_detail_like(df: pd.DataFrame) -> bool:
    if df is None or df.empty:
        return False
    norm_cols = {_norm_text(c) for c in df.columns}
    detail_markers = {
        "transaction_type",
        "approved_transaction_amount",
        "fraud_retention",
        "liberacion de fondos",
    }
    if detail_markers & norm_cols:
        return True
    return len(df.columns) >= 48


def _build_empty_result() -> Dict[str, Any]:
    return {
        "daily_summary": [],
        "merchant_detail": [],
        "total_net_deposit": 0.0,
        "row_count": 0,
    }


def _round_row_values(row: Dict[str, Any], numeric_fields: Sequence[str]) -> Dict[str, Any]:
    out = dict(row)
    for key in numeric_fields:
        if key == "tx_count":
            out[key] = int(round(float(out.get(key, 0) or 0), 0))
        else:
            out[key] = round(float(out.get(key, 0) or 0), 6)
    return out


def _parse_raw_settlement_detail(df: pd.DataFrame, filename: str) -> Dict[str, Any]:
    if df is None or df.empty:
        return _build_empty_result()

    df = _normalize_columns(df.copy())

    date_raw = _series_from_candidates(
        df,
        ["date"],
        fallback_idx=RAW_DETAIL_POSITION_MAP["date"],
    )
    merchant = _series_from_candidates(
        df,
        ["merchant_name"],
        fallback_idx=RAW_DETAIL_POSITION_MAP["merchant_name"],
    )
    status = _series_from_candidates(
        df,
        ["transaction_status"],
        fallback_idx=RAW_DETAIL_POSITION_MAP["transaction_status"],
    )
    tx_type = _series_from_candidates(
        df,
        ["transaction_type"],
        fallback_idx=RAW_DETAIL_POSITION_MAP["transaction_type"],
    )
    approved_amount = _series_from_candidates(
        df,
        ["approved_amount", "gross_amount"],
        fallback_idx=RAW_DETAIL_POSITION_MAP["approved_amount"],
    )
    kushki_comm = _series_from_candidates(
        df,
        ["kushki_commission"],
        fallback_idx=RAW_DETAIL_POSITION_MAP["kushki_commission"],
    )
    iva_comm = _series_from_candidates(
        df,
        ["iva_kushki_commission"],
        fallback_idx=RAW_DETAIL_POSITION_MAP["iva_kushki_commission"],
    )
    rr_retained = _series_from_candidates(
        df,
        ["rr_retained"],
        fallback_idx=RAW_DETAIL_POSITION_MAP["rr_retained"],
    )
    rr_released = _series_from_candidates(
        df,
        ["rr_released"],
        fallback_idx=RAW_DETAIL_POSITION_MAP["rr_released"],
    )
    net_deposit = _series_from_candidates(
        df,
        ["net_deposit"],
        fallback_idx=RAW_DETAIL_POSITION_MAP["net_deposit"],
    )

    normalized_date = date_raw.map(_normalize_date)
    valid_date_mask = normalized_date.map(_is_iso_date)

    parsed = pd.DataFrame({
        "row_date": normalized_date,
        "merchant_name": merchant.map(_canonical_merchant_name),
        "transaction_status": status.astype(str).str.strip().str.upper(),
        "transaction_type": tx_type.astype(str).str.strip().str.upper(),
        "approved_amount": _to_numeric_series(approved_amount),
        "kushki_commission": _to_numeric_series(kushki_comm),
        "iva_kushki_commission": _to_numeric_series(iva_comm),
        "rr_retained": _to_numeric_series(rr_retained),
        "rr_released": _to_numeric_series(rr_released),
        "net_deposit": _to_numeric_series(net_deposit),
    })

    # Spec: ignore rows where Fecha Pago is empty.
    parsed = parsed[valid_date_mask].copy()
    if parsed.empty:
        return _build_empty_result()

    settlement_date = _extract_filename_settlement_date(filename)
    if settlement_date:
        parsed["date"] = settlement_date
    else:
        parsed["date"] = parsed["row_date"]
    parsed = parsed.drop(columns=["row_date"])

    merchant_nonempty = parsed["merchant_name"].astype(str).str.strip().ne("")
    amount_cols = [
        "approved_amount",
        "kushki_commission",
        "iva_kushki_commission",
        "rr_retained",
        "rr_released",
        "net_deposit",
    ]
    has_values = parsed[amount_cols].abs().sum(axis=1) > 0
    parsed = parsed[merchant_nonempty | has_values].copy()
    if parsed.empty:
        return _build_empty_result()

    sale_approved = (
        parsed["transaction_type"].eq("SALE")
        & parsed["transaction_status"].eq("APPROVED")
    )
    is_refund = parsed["transaction_type"].eq("REFUND")
    is_chargeback = parsed["transaction_type"].eq("CHARGEBACK")
    is_void = parsed["transaction_type"].eq("VOID")
    is_manual = parsed["transaction_type"].eq("MANUAL")

    parsed["tx_count"] = sale_approved.astype(int)
    parsed["gross_amount"] = parsed["approved_amount"].where(sale_approved, 0.0)
    parsed["gross_adjustments"] = -parsed["approved_amount"].where(is_void, 0.0)
    parsed["refund"] = parsed["net_deposit"].where(is_refund, 0.0)
    parsed["chargeback"] = parsed["net_deposit"].where(is_chargeback, 0.0)
    parsed["void"] = parsed["net_deposit"].where(is_void, 0.0)
    parsed["manual"] = parsed["net_deposit"].where(is_manual, 0.0)
    parsed["commission"] = parsed["kushki_commission"] + parsed["iva_kushki_commission"]
    parsed["rolling_reserve"] = parsed["rr_retained"] - parsed["rr_released"]
    parsed["adjustments"] = parsed["refund"] + parsed["chargeback"] + parsed["void"] + parsed["manual"]
    parsed["net_verification"] = (
        parsed["gross_amount"]
        + parsed["gross_adjustments"]
        - parsed["commission"]
        - parsed["rr_retained"]
        + parsed["refund"]
        + parsed["chargeback"]
        + parsed["void"]
        + parsed["manual"]
        + parsed["rr_released"]
    )
    parsed["validation_diff"] = parsed["net_deposit"] - parsed["net_verification"]

    parsed["tonder_commission"] = 0.0
    parsed["tonder_iva"] = 0.0
    parsed["tonder_total"] = 0.0

    merchant_agg = (
        parsed.groupby(["date", "merchant_name"], as_index=False)
        .agg(
            tx_count=("tx_count", "sum"),
            gross_amount=("gross_amount", "sum"),
            gross_adjustments=("gross_adjustments", "sum"),
            commission=("commission", "sum"),
            kushki_commission=("kushki_commission", "sum"),
            iva_kushki_commission=("iva_kushki_commission", "sum"),
            rr_retained=("rr_retained", "sum"),
            rr_released=("rr_released", "sum"),
            tonder_commission=("tonder_commission", "sum"),
            tonder_iva=("tonder_iva", "sum"),
            tonder_total=("tonder_total", "sum"),
            refund=("refund", "sum"),
            chargeback=("chargeback", "sum"),
            void=("void", "sum"),
            manual=("manual", "sum"),
            adjustments=("adjustments", "sum"),
            rolling_reserve=("rolling_reserve", "sum"),
            net_deposit=("net_deposit", "sum"),
            net_verification=("net_verification", "sum"),
            validation_diff=("validation_diff", "sum"),
        )
    )
    merchant_agg["validation_diff"] = merchant_agg["net_deposit"] - merchant_agg["net_verification"]

    daily_agg = (
        merchant_agg.groupby("date", as_index=False)
        .agg(
            tx_count=("tx_count", "sum"),
            gross_amount=("gross_amount", "sum"),
            gross_adjustments=("gross_adjustments", "sum"),
            commission=("commission", "sum"),
            kushki_commission=("kushki_commission", "sum"),
            iva_kushki_commission=("iva_kushki_commission", "sum"),
            rr_retained=("rr_retained", "sum"),
            rr_released=("rr_released", "sum"),
            tonder_commission=("tonder_commission", "sum"),
            tonder_iva=("tonder_iva", "sum"),
            tonder_total=("tonder_total", "sum"),
            refund=("refund", "sum"),
            chargeback=("chargeback", "sum"),
            void=("void", "sum"),
            manual=("manual", "sum"),
            adjustments=("adjustments", "sum"),
            rolling_reserve=("rolling_reserve", "sum"),
            net_deposit=("net_deposit", "sum"),
            net_verification=("net_verification", "sum"),
            validation_diff=("validation_diff", "sum"),
        )
    )
    daily_agg["validation_diff"] = daily_agg["net_deposit"] - daily_agg["net_verification"]

    merchant_rows = []
    for _, row in merchant_agg.sort_values(by=["date", "merchant_name"]).iterrows():
        if _is_internal_merchant(row["merchant_name"]):
            continue
        merchant_row = {"date": row["date"], "merchant_name": str(row["merchant_name"]).strip() or "unknown"}
        for field in MERCHANT_NUMERIC_FIELDS:
            merchant_row[field] = row.get(field, 0)
        merchant_rows.append(_round_row_values(merchant_row, MERCHANT_NUMERIC_FIELDS))

    daily_rows = []
    for _, row in daily_agg.sort_values(by=["date"]).iterrows():
        daily_row = {"date": row["date"]}
        for field in DAILY_NUMERIC_FIELDS:
            daily_row[field] = row.get(field, 0)
        daily_rows.append(_round_row_values(daily_row, DAILY_NUMERIC_FIELDS))

    total_net = round(sum(r["net_deposit"] for r in daily_rows), 6)
    return {
        "daily_summary": daily_rows,
        "merchant_detail": merchant_rows,
        "total_net_deposit": total_net,
        "row_count": len(parsed),
    }

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
        "gross_adjustments": 0.0,
        "commission": 0.0,
        "kushki_commission": 0.0,
        "iva_kushki_commission": 0.0,
        "rr_retained": 0.0,
        "rr_released": 0.0,
        "tonder_commission": 0.0,
        "tonder_iva": 0.0,
        "tonder_total": 0.0,
        "refund": 0.0,
        "chargeback": 0.0,
        "void": 0.0,
        "manual": 0.0,
        "adjustments": 0.0,
        "net_deposit": 0.0,
    }
    for col, default_value in defaults.items():
        if col not in df.columns:
            df[col] = default_value

    if "rolling_reserve" in df.columns:
        roll = pd.to_numeric(df.get("rolling_reserve", 0), errors="coerce").fillna(0.0)
        rr_retained_current = pd.to_numeric(df.get("rr_retained", 0), errors="coerce").fillna(0.0)
        rr_released_current = pd.to_numeric(df.get("rr_released", 0), errors="coerce").fillna(0.0)
        if (not had_rr_retained) or rr_retained_current.abs().sum() == 0:
            df["rr_retained"] = roll.clip(lower=0)
        if (not had_rr_released) or rr_released_current.abs().sum() == 0:
            df["rr_released"] = (-roll).clip(lower=0)

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
        "gross_adjustments",
        "commission",
        "kushki_commission",
        "iva_kushki_commission",
        "rr_retained",
        "rr_released",
        "tonder_commission",
        "tonder_iva",
        "tonder_total",
        "refund",
        "chargeback",
        "void",
        "manual",
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


def _parse_legacy_summary(df: pd.DataFrame, filename: str, content: bytes) -> Dict[str, Any]:
    df = _prepare_kushki_df(df)
    if df.empty:
        return _build_empty_result()

    merchant_norm = df["merchant_name"].map(_norm_text)
    is_tonder = merchant_norm == "tonder"
    tonder_release = is_tonder.astype(float) * df["net_deposit"]
    df["rr_released_total"] = df["rr_released"].where(df["rr_released"] != 0, tonder_release)
    df["rolling_reserve"] = df["rr_retained"] - df["rr_released_total"]
    df["gross_adjustments"] = pd.to_numeric(df.get("gross_adjustments", 0), errors="coerce").fillna(0.0)
    df["refund"] = pd.to_numeric(df.get("refund", 0), errors="coerce").fillna(0.0)
    df["chargeback"] = pd.to_numeric(df.get("chargeback", 0), errors="coerce").fillna(0.0)
    df["void"] = pd.to_numeric(df.get("void", 0), errors="coerce").fillna(0.0)
    df["manual"] = pd.to_numeric(df.get("manual", 0), errors="coerce").fillna(0.0)
    if df["adjustments"].abs().sum() == 0:
        df["adjustments"] = df["refund"] + df["chargeback"] + df["void"] + df["manual"]

    df["net_verification"] = (
        df["gross_amount"]
        + df["gross_adjustments"]
        - df["commission"]
        - df["rr_retained"]
        + df["refund"]
        + df["chargeback"]
        + df["void"]
        + df["manual"]
        + df["rr_released_total"]
    )
    df["validation_diff"] = df["net_deposit"] - df["net_verification"]

    merchant_source = df[~is_tonder].copy()

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
                    detail_df["gross_adjustments"] = pd.to_numeric(
                        detail_df.get("gross_adjustments", 0), errors="coerce"
                    ).fillna(0.0)
                    detail_df["refund"] = pd.to_numeric(detail_df.get("refund", 0), errors="coerce").fillna(0.0)
                    detail_df["chargeback"] = pd.to_numeric(
                        detail_df.get("chargeback", 0), errors="coerce"
                    ).fillna(0.0)
                    detail_df["void"] = pd.to_numeric(detail_df.get("void", 0), errors="coerce").fillna(0.0)
                    detail_df["manual"] = pd.to_numeric(detail_df.get("manual", 0), errors="coerce").fillna(0.0)
                    if detail_df["adjustments"].abs().sum() == 0:
                        detail_df["adjustments"] = (
                            detail_df["refund"] + detail_df["chargeback"] + detail_df["void"] + detail_df["manual"]
                        )
                    detail_df["net_verification"] = (
                        detail_df["gross_amount"]
                        + detail_df["gross_adjustments"]
                        - detail_df["commission"]
                        - detail_df["rr_retained"]
                        + detail_df["refund"]
                        + detail_df["chargeback"]
                        + detail_df["void"]
                        + detail_df["manual"]
                        + detail_df["rr_released_total"]
                    )
                    detail_df["validation_diff"] = detail_df["net_deposit"] - detail_df["net_verification"]
                    merchant_source = detail_df[~detail_is_tonder].copy()
        except Exception as exc:
            logger.warning(f"Unable to parse Detalle por Merchant sheet from {filename}: {exc}")

    daily = (
        df.groupby("date", as_index=False)
        .agg(
            tx_count=("tx_count", "sum"),
            gross_amount=("gross_amount", "sum"),
            gross_adjustments=("gross_adjustments", "sum"),
            commission=("commission", "sum"),
            kushki_commission=("kushki_commission", "sum"),
            iva_kushki_commission=("iva_kushki_commission", "sum"),
            rr_retained=("rr_retained", "sum"),
            rr_released=("rr_released_total", "sum"),
            tonder_commission=("tonder_commission", "sum"),
            tonder_iva=("tonder_iva", "sum"),
            tonder_total=("tonder_total", "sum"),
            refund=("refund", "sum"),
            chargeback=("chargeback", "sum"),
            void=("void", "sum"),
            manual=("manual", "sum"),
            adjustments=("adjustments", "sum"),
            rolling_reserve=("rolling_reserve", "sum"),
            net_deposit=("net_deposit", "sum"),
            net_verification=("net_verification", "sum"),
            validation_diff=("validation_diff", "sum"),
        )
    )
    daily["validation_diff"] = daily["net_deposit"] - daily["net_verification"]

    daily_summary: List[Dict[str, Any]] = []
    for _, row in daily.sort_values(by=["date"]).iterrows():
        daily_row = {"date": row["date"]}
        for field in DAILY_NUMERIC_FIELDS:
            daily_row[field] = row.get(field, 0)
        daily_summary.append(_round_row_values(daily_row, DAILY_NUMERIC_FIELDS))

    merchant_detail: List[Dict[str, Any]] = []
    if not merchant_source.empty:
        merchant = (
            merchant_source.groupby(["date", "merchant_name"], as_index=False)
            .agg(
                tx_count=("tx_count", "sum"),
                gross_amount=("gross_amount", "sum"),
                gross_adjustments=("gross_adjustments", "sum"),
                commission=("commission", "sum"),
                kushki_commission=("kushki_commission", "sum"),
                iva_kushki_commission=("iva_kushki_commission", "sum"),
                rr_retained=("rr_retained", "sum"),
                rr_released=("rr_released_total", "sum"),
                tonder_commission=("tonder_commission", "sum"),
                tonder_iva=("tonder_iva", "sum"),
                tonder_total=("tonder_total", "sum"),
                refund=("refund", "sum"),
                chargeback=("chargeback", "sum"),
                void=("void", "sum"),
                manual=("manual", "sum"),
                adjustments=("adjustments", "sum"),
                rolling_reserve=("rolling_reserve", "sum"),
                net_deposit=("net_deposit", "sum"),
                net_verification=("net_verification", "sum"),
                validation_diff=("validation_diff", "sum"),
            )
        )
        merchant["validation_diff"] = merchant["net_deposit"] - merchant["net_verification"]
        for _, row in merchant.sort_values(by=["date", "merchant_name"]).iterrows():
            merchant_row = {"date": row["date"], "merchant_name": str(row["merchant_name"]).strip() or "unknown"}
            for field in MERCHANT_NUMERIC_FIELDS:
                merchant_row[field] = row.get(field, 0)
            merchant_detail.append(_round_row_values(merchant_row, MERCHANT_NUMERIC_FIELDS))

    total_net = round(sum(r["net_deposit"] for r in daily_summary), 6)
    return {
        "daily_summary": daily_summary,
        "merchant_detail": merchant_detail,
        "total_net_deposit": total_net,
        "row_count": len(df),
    }


def parse_kushki(content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse one Kushki file.
    Returns daily_summary and merchant_detail.
    """
    fname = str(filename or "").lower()

    # 1) Prefer raw settlement logic when "Detalle de Liquidacion" is available.
    if fname.endswith((".xlsx", ".xls")):
        try:
            xls = pd.ExcelFile(io.BytesIO(content))
            if "Detalle de Liquidacion" in xls.sheet_names:
                raw_df = _read_excel_sheet(content, "Detalle de Liquidacion")
                parsed = _parse_raw_settlement_detail(raw_df, filename)
                if parsed["row_count"] > 0:
                    return parsed
        except Exception as exc:
            logger.warning(f"Unable to parse raw settlement sheet from {filename}: {exc}")

    # 2) Parse file with generic loader; if still raw-like, use raw settlement logic.
    df = _parse_file(content, filename)
    if _is_raw_detail_like(df):
        parsed = _parse_raw_settlement_detail(df, filename)
        if parsed["row_count"] > 0:
            return parsed

    # 3) Fallback to legacy summarized parser.
    return _parse_legacy_summary(df, filename, content)


def merge_kushki_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Consolidate multiple Kushki parsed outputs into a single clean monthly dataset.
    This avoids duplicated rows when the month arrives split across many files.
    """
    daily_acc = defaultdict(lambda: {field: 0.0 for field in DAILY_NUMERIC_FIELDS})
    merchant_acc = defaultdict(lambda: {field: 0.0 for field in MERCHANT_NUMERIC_FIELDS})

    for result in results:
        for row in result.get("daily_summary", []) or []:
            day = str(row.get("date", "")).strip()
            if not day:
                continue
            for field in DAILY_NUMERIC_FIELDS:
                daily_acc[day][field] += float(row.get(field, 0) or 0)

        for row in result.get("merchant_detail", []) or []:
            day = str(row.get("date", "")).strip()
            merchant = _canonical_merchant_name(row.get("merchant_name", "unknown")) or "unknown"
            if not day:
                continue
            key = (day, merchant)
            for field in MERCHANT_NUMERIC_FIELDS:
                merchant_acc[key][field] += float(row.get(field, 0) or 0)

    daily_summary: List[Dict[str, Any]] = []
    for day, data in sorted(daily_acc.items(), key=lambda x: x[0]):
        row = {"date": day}
        row.update(data)
        row["validation_diff"] = row.get("net_deposit", 0.0) - row.get("net_verification", 0.0)
        daily_summary.append(_round_row_values(row, DAILY_NUMERIC_FIELDS))

    merchant_detail: List[Dict[str, Any]] = []
    for (day, merchant), data in sorted(merchant_acc.items(), key=lambda x: (x[0][0], x[0][1].lower())):
        row = {"date": day, "merchant_name": merchant}
        row.update(data)
        row["validation_diff"] = row.get("net_deposit", 0.0) - row.get("net_verification", 0.0)
        merchant_detail.append(_round_row_values(row, MERCHANT_NUMERIC_FIELDS))

    total_net = round(sum(r["net_deposit"] for r in daily_summary), 6)
    return {
        "daily_summary": daily_summary,
        "merchant_detail": merchant_detail,
        "total_net_deposit": total_net,
    }


def _date_from_iso(value: str) -> Optional[date]:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def _iter_days(start: date, end: date) -> List[str]:
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def _resolve_fees_merchant(
    kushki_merchant: str,
    period_year: int,
    period_month: int,
    known_kushki_fee_merchants: set,
) -> str:
    norm = _norm_text(kushki_merchant)
    mapped = KUSHKI_TO_FEES_MAP.get(norm, "")
    if mapped == "__BEXAR_GENERIC__":
        mapped = "Paradise" if (period_year == 2026 and period_month == 3) else ""
    if mapped:
        return mapped

    # Safe fallback: if merchant name already exists in FEES kushki concept rows, use it.
    if norm in known_kushki_fee_merchants:
        return kushki_merchant
    return ""


def _extract_fee_value(row: Dict[str, Any]) -> float:
    return float(row.get("fee_amount", row.get("total_fee", 0)) or 0)


def enrich_kushki_with_fees(
    kushki_data: Dict[str, Any],
    fees_data: Optional[Dict[str, Any]],
    period_year: int,
    period_month: int,
) -> Dict[str, Any]:
    """
    Enrich Kushki settlement data with FEES per settlement period (PDF spec).
    - Daily (Resumen Diario): includes all concepts in period.
    - Merchant detail: includes only concept rows containing "Kushki".
    """
    if not kushki_data:
        return kushki_data

    daily_summary = list(kushki_data.get("daily_summary", []) or [])
    merchant_detail = list(kushki_data.get("merchant_detail", []) or [])
    if not daily_summary:
        return kushki_data

    fees_daily_rows = []
    if fees_data and isinstance(fees_data, dict):
        fees_daily_rows = list(fees_data.get("daily_breakdown", []) or [])

    fees_total_by_day = defaultdict(float)
    fees_kushki_by_day_merchant = defaultdict(float)
    known_kushki_fee_merchants = set()

    for row in fees_daily_rows:
        day = _normalize_date(row.get("date"))
        if not _is_iso_date(day):
            continue
        d = _date_from_iso(day)
        if d is None or d.year != int(period_year) or d.month != int(period_month):
            continue

        amount = _extract_fee_value(row)
        merchant_name = str(row.get("merchant_name") or row.get("merchant_id") or "").strip()
        merchant_norm = _norm_text(merchant_name)
        concept_seed = " ".join(
            [
                str(row.get("concepto") or ""),
                str(row.get("concept") or ""),
                str(row.get("acquirer") or ""),
            ]
        )
        concept_norm = _norm_text(concept_seed)
        is_kushki_concept = "kushki" in concept_norm

        fees_total_by_day[day] += amount
        if is_kushki_concept and merchant_norm:
            known_kushki_fee_merchants.add(merchant_norm)
            fees_kushki_by_day_merchant[(day, merchant_norm)] += amount

    settlement_dates = sorted({str(r.get("date", "")).strip() for r in daily_summary if _is_iso_date(r.get("date"))})
    if not settlement_dates:
        return kushki_data

    period_lookup: Dict[str, Dict[str, Any]] = {}
    month_start = date(int(period_year), int(period_month), 1)

    for idx, day in enumerate(settlement_dates):
        settlement_day = _date_from_iso(day)
        if settlement_day is None:
            continue
        if idx == 0:
            start_day = month_start
        else:
            prev_day = _date_from_iso(settlement_dates[idx - 1])
            start_day = (prev_day + timedelta(days=1)) if prev_day else month_start
        period_days = _iter_days(start_day, settlement_day)
        fee_total = sum(fees_total_by_day.get(d, 0.0) for d in period_days)
        period_lookup[day] = {
            "period_start": start_day.isoformat(),
            "period_end": settlement_day.isoformat(),
            "period_days": len(period_days),
            "period_dates": period_days,
            "fee_total": round(fee_total, 6),
        }

    unmapped_merchants = set()

    enriched_merchant = []
    for row in merchant_detail:
        day = str(row.get("date", "")).strip()
        period_info = period_lookup.get(day)
        if not period_info:
            enriched_merchant.append(row)
            continue

        merchant_name = str(row.get("merchant_name") or "").strip()
        mapped_fee_name = _resolve_fees_merchant(
            merchant_name,
            period_year=int(period_year),
            period_month=int(period_month),
            known_kushki_fee_merchants=known_kushki_fee_merchants,
        )
        mapped_norm = _norm_text(mapped_fee_name)

        tonder_commission = 0.0
        if mapped_norm:
            tonder_commission = sum(
                fees_kushki_by_day_merchant.get((d, mapped_norm), 0.0)
                for d in period_info["period_dates"]
            )

        if not mapped_fee_name and not _is_internal_merchant(merchant_name):
            unmapped_merchants.add(merchant_name)

        commission_total = float(row.get("commission", 0) or 0)
        gross = float(row.get("gross_amount", 0) or 0)
        gross_adj = float(row.get("gross_adjustments", 0) or 0)
        rr_retained = float(row.get("rr_retained", 0) or 0)
        refund = float(row.get("refund", 0) or 0)
        chargeback = float(row.get("chargeback", 0) or 0)
        void = float(row.get("void", 0) or 0)
        manual = float(row.get("manual", 0) or 0)
        rr_released = float(row.get("rr_released", 0) or 0)
        net = float(row.get("net_deposit", 0) or 0)

        net_verification = (
            gross + gross_adj - commission_total - rr_retained + refund + chargeback + void + manual + rr_released
        )

        updated = dict(row)
        updated["fees_merchant_name"] = mapped_fee_name
        updated["period_start"] = period_info["period_start"]
        updated["period_end"] = period_info["period_end"]
        updated["period_days"] = period_info["period_days"]
        updated["tonder_commission"] = round(tonder_commission, 6)
        updated["tonder_iva"] = round(tonder_commission * 0.16, 6)
        updated["tonder_total"] = round(updated["tonder_commission"] + updated["tonder_iva"], 6)
        updated["adjustments"] = round(refund + chargeback + void + manual, 6)
        updated["rolling_reserve"] = round(rr_retained - rr_released, 6)
        updated["net_verification"] = round(net_verification, 6)
        updated["validation_diff"] = round(net - net_verification, 6)
        enriched_merchant.append(_round_row_values(updated, MERCHANT_NUMERIC_FIELDS))

    enriched_daily = []
    for row in daily_summary:
        day = str(row.get("date", "")).strip()
        period_info = period_lookup.get(day, {})
        fee_total = float(period_info.get("fee_total", 0) or 0)

        commission_total = float(row.get("commission", 0) or 0)
        gross = float(row.get("gross_amount", 0) or 0)
        gross_adj = float(row.get("gross_adjustments", 0) or 0)
        rr_retained = float(row.get("rr_retained", 0) or 0)
        refund = float(row.get("refund", 0) or 0)
        chargeback = float(row.get("chargeback", 0) or 0)
        void = float(row.get("void", 0) or 0)
        manual = float(row.get("manual", 0) or 0)
        rr_released = float(row.get("rr_released", 0) or 0)
        net = float(row.get("net_deposit", 0) or 0)

        net_verification = (
            gross + gross_adj - commission_total - rr_retained + refund + chargeback + void + manual + rr_released
        )

        updated = dict(row)
        updated["period_start"] = period_info.get("period_start", "")
        updated["period_end"] = period_info.get("period_end", "")
        updated["period_days"] = int(period_info.get("period_days", 0) or 0)
        updated["tonder_commission"] = round(fee_total, 6)
        updated["tonder_iva"] = round(fee_total * 0.16, 6)
        updated["tonder_total"] = round(updated["tonder_commission"] + updated["tonder_iva"], 6)
        updated["adjustments"] = round(refund + chargeback + void + manual, 6)
        updated["rolling_reserve"] = round(rr_retained - rr_released, 6)
        updated["net_verification"] = round(net_verification, 6)
        updated["validation_diff"] = round(net - net_verification, 6)
        enriched_daily.append(_round_row_values(updated, DAILY_NUMERIC_FIELDS))

    enriched_daily.sort(key=lambda r: str(r.get("date", "")))
    enriched_merchant.sort(key=lambda r: (str(r.get("date", "")), _norm_text(r.get("merchant_name", ""))))
    total_net = round(sum(float(r.get("net_deposit", 0) or 0) for r in enriched_daily), 6)

    out = dict(kushki_data)
    out["daily_summary"] = enriched_daily
    out["merchant_detail"] = enriched_merchant
    out["total_net_deposit"] = total_net
    out["unmapped_merchants"] = sorted(unmapped_merchants, key=lambda x: _norm_text(x))
    return out
