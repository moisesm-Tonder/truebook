from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Numeric
from sqlalchemy.sql import func
from app.database import Base


class FeesResult(Base):
    __tablename__ = "fees_results"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("accounting_processes.id", ondelete="CASCADE"), unique=True)
    merchant_summary = Column(JSON, nullable=True)   # [{merchant, total_fee, tx_count, ...}]
    daily_breakdown = Column(JSON, nullable=True)    # [{date, merchant, fee_amount, ...}]
    withdrawals_summary = Column(JSON, nullable=True)
    refunds_summary = Column(JSON, nullable=True)
    other_fees_summary = Column(JSON, nullable=True)
    total_fees = Column(Numeric(18, 6), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KushkiResult(Base):
    __tablename__ = "kushki_results"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("accounting_processes.id", ondelete="CASCADE"), unique=True)
    daily_summary = Column(JSON, nullable=True)      # [{date, tx_count, gross, commission, rolling_reserve, net_deposit}]
    merchant_detail = Column(JSON, nullable=True)    # [{merchant, ...}]
    total_net_deposit = Column(Numeric(18, 6), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BanregioResult(Base):
    __tablename__ = "banregio_results"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("accounting_processes.id", ondelete="CASCADE"), unique=True)
    movements = Column(JSON, nullable=True)
    summary = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ConciliationResult(Base):
    __tablename__ = "conciliation_results"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("accounting_processes.id", ondelete="CASCADE"))
    conciliation_type = Column(String, nullable=False)  # fees | kushki_daily | kushki_vs_banregio
    matched = Column(JSON, nullable=True)
    differences = Column(JSON, nullable=True)
    unmatched_kushki = Column(JSON, nullable=True)
    unmatched_banregio = Column(JSON, nullable=True)
    total_conciliated = Column(Numeric(18, 6), nullable=True)
    total_difference = Column(Numeric(18, 6), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
