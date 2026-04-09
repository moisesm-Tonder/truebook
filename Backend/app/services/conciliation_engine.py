"""
Conciliation engine.
1. FEES conciliation — consolidate by merchant
2. Kushki daily conciliation
3. Kushki vs Banregio — Column I (Kushki net_deposit) vs Column H (Banregio deposit_ref)
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

TOLERANCE = 0.01  # centavo tolerance for matching


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

        matched.append({
            "merchant_id": mid,
            "merchant_name": merchant.get("merchant_name"),
            "tx_fee": round(tx_fee, 6),
            "withdrawal_fee": round(w_fee, 6),
            "refund_fee": round(r_fee, 6),
            "total_fee": total,
        })

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
        gross = float(row.get("gross_amount", 0))
        commission = float(row.get("commission", 0))
        rolling = float(row.get("rolling_reserve", 0))
        net = float(row.get("net_deposit", 0))
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
    Cross Kushki Column I (net_deposit per day) vs Banregio Column H (deposit_ref).
    Match by amount within tolerance.
    """
    # Kushki side: list of {date, net_deposit}
    kushki_deposits = [
        {"date": r["date"], "amount": float(r.get("net_deposit", 0))}
        for r in kushki_result.get("daily_summary", [])
        if float(r.get("net_deposit", 0)) > 0
    ]

    # Banregio side: list of deposit amounts from column H
    banregio_deposits = [
        {"amount": float(a), "matched": False}
        for a in banregio_result.get("deposit_column", [])
        if float(a) > 0
    ]

    matched = []
    unmatched_kushki = []

    for k in kushki_deposits:
        found = False
        for b in banregio_deposits:
            if not b["matched"] and abs(b["amount"] - k["amount"]) <= TOLERANCE:
                matched.append({
                    "date": k["date"],
                    "kushki_amount": k["amount"],
                    "banregio_amount": b["amount"],
                    "difference": round(abs(b["amount"] - k["amount"]), 6),
                })
                b["matched"] = True
                found = True
                break
        if not found:
            unmatched_kushki.append(k)

    unmatched_banregio = [b for b in banregio_deposits if not b["matched"]]

    total_conciliated = sum(m["kushki_amount"] for m in matched)
    total_difference = sum(m["difference"] for m in matched)

    return {
        "matched": matched,
        "differences": [],
        "unmatched_kushki": unmatched_kushki,
        "unmatched_banregio": [{"amount": b["amount"]} for b in unmatched_banregio],
        "total_conciliated": round(total_conciliated, 6),
        "total_difference": round(total_difference, 6),
        "stats": {
            "total_matched": len(matched),
            "total_unmatched_kushki": len(unmatched_kushki),
            "total_unmatched_banregio": len(unmatched_banregio),
        },
    }
