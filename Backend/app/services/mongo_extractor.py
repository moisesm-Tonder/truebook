"""
MongoDB extractor for FEES TONDER process.
Extracts mv_payment_transactions, usrv-withdrawals-withdrawals, usrv-deposits-refunds.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from app.config import settings

logger = logging.getLogger(__name__)

# UTC-6 offset
TZ_OFFSET = timedelta(hours=6)


def _get_period_range(year: int, month: int):
    """Returns (start_utc, end_utc) for the accounting period UTC-6."""
    # Start: day 1 of month at 06:00:00 UTC (= 00:00:00 UTC-6)
    start_utc = datetime(year, month, 1, 6, 0, 0, tzinfo=timezone.utc)
    # End: day 1 of next month at 05:59:59 UTC
    if month == 12:
        end_utc = datetime(year + 1, 1, 1, 5, 59, 59, tzinfo=timezone.utc)
    else:
        end_utc = datetime(year, month + 1, 1, 5, 59, 59, tzinfo=timezone.utc)
    return start_utc, end_utc


def _get_client() -> MongoClient:
    return MongoClient(
        settings.MONGO_URI,
        connectTimeoutMS=settings.MONGO_CONNECT_TIMEOUT_MS,
        socketTimeoutMS=settings.MONGO_SOCKET_TIMEOUT_MS,
        serverSelectionTimeoutMS=settings.MONGO_CONNECT_TIMEOUT_MS,
    )


def extract_transactions(year: int, month: int, acquirers: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Extract successful payment transactions from MongoDB for the given period."""
    start_utc, end_utc = _get_period_range(year, month)
    logger.info(f"Extracting transactions {start_utc} → {end_utc}, acquirers={acquirers}")

    client = _get_client()
    try:
        db = client[settings.MONGO_DATABASE]
        collection = db[settings.MONGO_COLLECTION]

        query: Dict[str, Any] = {
            "status": "success",
            "created_at": {"$gte": start_utc, "$lte": end_utc},
        }
        if acquirers:
            query["acquirer_name"] = {"$in": acquirers}

        projection = {
            "_id": 0,
            "transaction_id": 1,
            "merchant_id": 1,
            "merchant_name": 1,
            "acquirer_name": 1,
            "amount": 1,
            "fee_amount": 1,
            "is_fees_computed": 1,
            "msa": 1,
            "created_at": 1,
            "currency": 1,
            "status": 1,
        }

        results = list(collection.find(query, projection))
        logger.info(f"Extracted {len(results)} transactions")
        return results
    finally:
        client.close()


def extract_withdrawals(year: int, month: int) -> List[Dict[str, Any]]:
    """Extract PAID_FULL withdrawals for the period using last_sync date."""
    start_utc, end_utc = _get_period_range(year, month)
    logger.info(f"Extracting withdrawals {start_utc} → {end_utc}")

    client = _get_client()
    try:
        db = client[settings.MONGO_DATABASE]
        collection = db["usrv-withdrawals-withdrawals"]

        query = {
            "status": "PAID_FULL",
            "last_sync": {"$gte": start_utc, "$lte": end_utc},
        }
        projection = {
            "_id": 0,
            "withdrawal_id": 1,
            "merchant_id": 1,
            "merchant_name": 1,
            "amount": 1,
            "fee_amount": 1,
            "msa": 1,
            "status": 1,
            "last_sync": 1,
        }
        results = list(collection.find(query, projection))
        logger.info(f"Extracted {len(results)} withdrawals")
        return results
    finally:
        client.close()


def extract_refunds(year: int, month: int) -> List[Dict[str, Any]]:
    """Extract complete refunds/autorefunds for the period."""
    start_utc, end_utc = _get_period_range(year, month)
    logger.info(f"Extracting refunds {start_utc} → {end_utc}")

    client = _get_client()
    try:
        db = client[settings.MONGO_DATABASE]
        collection = db["usrv-deposits-refunds"]

        query = {
            "status": "complete",
            "created_at": {"$gte": start_utc, "$lte": end_utc},
        }
        projection = {
            "_id": 0,
            "refund_id": 1,
            "merchant_id": 1,
            "merchant_name": 1,
            "amount": 1,
            "fee_amount": 1,
            "msa": 1,
            "type": 1,
            "status": 1,
            "created_at": 1,
        }
        results = list(collection.find(query, projection))
        logger.info(f"Extracted {len(results)} refunds/autorefunds")
        return results
    finally:
        client.close()
