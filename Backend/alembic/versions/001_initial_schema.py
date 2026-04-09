"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("role", sa.String(), default="analyst"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "accounting_processes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("acquirers", postgresql.JSON(), nullable=True),
        sa.Column("status", sa.String(), default="pending"),
        sa.Column("current_stage", sa.String(), nullable=True),
        sa.Column("progress", sa.Integer(), default=0),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    op.create_table(
        "process_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("accounting_processes.id", ondelete="CASCADE")),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("level", sa.String(), default="info"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "uploaded_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("accounting_processes.id", ondelete="CASCADE")),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("original_name", sa.String(), nullable=False),
        sa.Column("stored_path", sa.String(), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(), default="uploaded"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fees_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("accounting_processes.id", ondelete="CASCADE"), unique=True),
        sa.Column("merchant_summary", postgresql.JSON(), nullable=True),
        sa.Column("daily_breakdown", postgresql.JSON(), nullable=True),
        sa.Column("withdrawals_summary", postgresql.JSON(), nullable=True),
        sa.Column("refunds_summary", postgresql.JSON(), nullable=True),
        sa.Column("other_fees_summary", postgresql.JSON(), nullable=True),
        sa.Column("total_fees", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "kushki_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("accounting_processes.id", ondelete="CASCADE"), unique=True),
        sa.Column("daily_summary", postgresql.JSON(), nullable=True),
        sa.Column("merchant_detail", postgresql.JSON(), nullable=True),
        sa.Column("total_net_deposit", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "banregio_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("accounting_processes.id", ondelete="CASCADE"), unique=True),
        sa.Column("movements", postgresql.JSON(), nullable=True),
        sa.Column("summary", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "conciliation_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("accounting_processes.id", ondelete="CASCADE")),
        sa.Column("conciliation_type", sa.String(), nullable=False),
        sa.Column("matched", postgresql.JSON(), nullable=True),
        sa.Column("differences", postgresql.JSON(), nullable=True),
        sa.Column("unmatched_kushki", postgresql.JSON(), nullable=True),
        sa.Column("unmatched_banregio", postgresql.JSON(), nullable=True),
        sa.Column("total_conciliated", sa.Numeric(18, 6), nullable=True),
        sa.Column("total_difference", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "integration_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), unique=True, nullable=False),
        sa.Column("config_type", sa.String(), nullable=False),
        sa.Column("config_value", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for tbl in ["integration_configs", "conciliation_results", "banregio_results",
                "kushki_results", "fees_results", "uploaded_files",
                "process_logs", "accounting_processes", "users"]:
        op.drop_table(tbl)
