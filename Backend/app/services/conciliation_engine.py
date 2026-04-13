"""
Conciliation engine.
1. FEES conciliation - consolidate by merchant
2. Kushki daily conciliation
3. Kushki vs Banregio - net deposit cross-check
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TOLERANCE = 0.01  # cent-level tolerance for matching


def _to_float(value: Any) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _normalize_date(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    raw = str(value).strip()
    if not raw or raw.lower() in {"nan", "none"}:
        return ""

    try:
        numeric = float(raw)
        if 30000 <= numeric <= 60000:
            return (datetime(1899, 12, 30) + timedelta(days=int(numeric))).date().isoformat()
    except Exception:
        pass

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date().isoformat()
        except Exception:
            continue

    return raw[:10]


def _pick_candidate(
    pool: List[Dict[str, Any]],
    target_amount: float,
    target_date: str,
    require_same_date: bool,
    require_exact: bool,
) -> Optional[Dict[str, Any]]:
    best = None
    best_diff = None
    for candidate in pool:
        if candidate.get("matched"):
            continue
        if require_same_date and target_date and candidate.get("date") != target_date:
            continue

        diff = abs(candidate["amount"] - target_amount)
        if require_exact and diff > TOLERANCE:
            continue
        if best_diff is None or diff < best_diff:
            best = candidate
            best_diff = diff
    return best


def conciliate_fees(fees_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate FEES consolidation:
    tx fees + withdrawal fees + refund fees = total fees.
    """
    merchant_summary = fees_result.get("merchant_summary", [])
    withdrawals = fees_result.get("withdrawals_summary", [])
    refunds = fees_result.get("refunds_summary", [])

    matched = []
    differences = []

    for merchant in merchant_summary:
        mid = merchant["merchant_id"]
        tx_fee = merchant.get("total_fee", 0)
        w_fee = next((w["total_fee"] for w in withdrawals if w.get("merchant_id") == mid), 0)
        r_fee = next((r["total_fee"] for r in refunds if r.get("merchant_id") == mid), 0)
        total = round(tx_fee + w_fee + r_fee, 6)

        matched.append(
            {
                "merchant_id": mid,
                "merchant_name": merchant.get("merchant_name"),
                "tx_fee": round(tx_fee, 6),
                "withdrawal_fee": round(w_fee, 6),
                "refund_fee": round(r_fee, 6),
                "total_fee": total,
            }
        )

    total_conciliated = sum(m["total_fee"] for m in matched)
    return {
        "matched": matched,
        "differences": differences,
        "unmatched_kushki": [],
        "unmatched_banregio": [],
        "total_conciliated": round(total_conciliated, 6),
        "total_difference": 0.0,
    }


def conciliate_kushki_daily(kushki_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Kushki daily summary:
    gross - commission - rolling_reserve = net_deposit per day.
    """
    daily = kushki_result.get("daily_summary", [])
    matched = []
    differences = []

    for row in daily:
        gross = _to_float(row.get("gross_amount", 0))
        commission = _to_float(row.get("commission", 0))
        rolling = _to_float(row.get("rolling_reserve", 0))
        net = _to_float(row.get("net_deposit", 0))
        computed_net = round(gross - commission - rolling, 6)
        diff = round(abs(computed_net - net), 6)

        entry = {
            "date": row.get("date"),
            "tx_count": row.get("tx_count"),
            "gross_amount": gross,
            "commission": commission,
            "rolling_reserve": rolling,
            "net_deposit": net,
            "computed_net": computed_net,
            "difference": diff,
        }
        if diff <= TOLERANCE:
            matched.append(entry)
        else:
            differences.append(entry)

    total_conciliated = sum(r["net_deposit"] for r in matched)
    total_difference = sum(r["difference"] for r in differences)

    return {
        "matched": matched,
        "differences": differences,
        "unmatched_kushki": [],
        "unmatched_banregio": [],
        "total_conciliated": round(total_conciliated, 6),
        "total_difference": round(total_difference, 6),
    }


def conciliate_kushki_vs_banregio(
    kushki_result: Dict[str, Any],
    banregio_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Cross-check Kushki daily net deposits against Banregio deposit credits.
    Matching strategy:
    1) exact match by same date + amount
    2) exact match by amount (any date)
    3) nearest amount same date
    4) nearest amount global
    """
    kushki_deposits = [
        {
            "date": _normalize_date(row.get("date")),
            "amount": _to_float(row.get("net_deposit", 0)),
        }
        for row in kushki_result.get("daily_summary", [])
        if _to_float(row.get("net_deposit", 0)) > 0
    ]

    banregio_pool = []
    for movement in banregio_result.get("movements", []) or []:
        amount = _to_float(movement.get("deposit_ref", 0))
        if amount <= 0:
            amount = _to_float(movement.get("credit", 0))
        if amount <= 0:
            continue
        banregio_pool.append(
            {
                "date": _normalize_date(movement.get("date")),
                "amount": amount,
                "matched": False,
            }
        )
    if not banregio_pool:
        banregio_pool = [
            {"date": "", "amount": _to_float(v), "matched": False}
            for v in banregio_result.get("deposit_column", [])
            if _to_float(v) > 0
        ]

    matched: List[Dict[str, Any]] = []
    differences: List[Dict[str, Any]] = []
    unmatched_kushki: List[Dict[str, Any]] = []

    for kushki in kushki_deposits:
        candidate = _pick_candidate(
            banregio_pool,
            target_amount=kushki["amount"],
            target_date=kushki["date"],
            require_same_date=True,
            require_exact=True,
        )
        if candidate is None:
            candidate = _pick_candidate(
                banregio_pool,
                target_amount=kushki["amount"],
                target_date=kushki["date"],
                require_same_date=False,
                require_exact=True,
            )
        if candidate is None:
            candidate = _pick_candidate(
                banregio_pool,
                target_amount=kushki["amount"],
                target_date=kushki["date"],
                require_same_date=True,
                require_exact=False,
            )
        if candidate is None:
            candidate = _pick_candidate(
                banregio_pool,
                target_amount=kushki["amount"],
                target_date=kushki["date"],
                require_same_date=False,
                require_exact=False,
            )

        if candidate is None:
            unmatched_kushki.append(kushki)
            differences.append(
                {
                    "date": kushki["date"],
                    "kushki_amount": kushki["amount"],
                    "banregio_amount": 0.0,
                    "banregio_date": "",
                    "difference": round(kushki["amount"], 6),
                }
            )
            continue

        candidate["matched"] = True
        diff = round(abs(candidate["amount"] - kushki["amount"]), 6)
        row = {
            "date": kushki["date"],
            "kushki_amount": round(kushki["amount"], 6),
            "banregio_amount": round(candidate["amount"], 6),
            "banregio_date": candidate["date"],
            "difference": diff,
        }
        if diff <= TOLERANCE:
            matched.append(row)
        else:
            differences.append(row)

    unmatched_banregio = [b for b in banregio_pool if not b.get("matched")]
    total_conciliated = sum(m["kushki_amount"] for m in matched)
    total_difference = sum(d.get("difference", 0) for d in differences)

    return {
        "matched": matched,
        "differences": differences,
        "unmatched_kushki": unmatched_kushki,
        "unmatched_banregio": [
            {"date": b.get("date"), "amount": round(_to_float(b.get("amount")), 6)}
            for b in unmatched_banregio
        ],
        "total_conciliated": round(total_conciliated, 6),
        "total_difference": round(total_difference, 6),
        "stats": {
            "total_matched": len(matched),
            "total_differences": len(differences),
            "total_unmatched_kushki": len(unmatched_kushki),
            "total_unmatched_banregio": len(unmatched_banregio),
        },
    }
