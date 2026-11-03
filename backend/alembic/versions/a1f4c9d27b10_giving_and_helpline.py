"""Hindi scheme text, payment failure reason, monthly mandates and helpline call-backs.

Revision ID: a1f4c9d27b10
Revises: c5716c687fae
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a1f4c9d27b10"
down_revision: str | None = "c5716c687fae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in ("who_can_apply_hi", "how_to_apply_hi", "help_centre_hi"):
        op.add_column("schemes", sa.Column(column, sa.Text(), server_default="", nullable=False))
    op.add_column(
        "schemes",
        sa.Column(
            "documents_hi",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )
    op.add_column("donations", sa.Column("failure_reason", sa.String(30), nullable=True))
    op.create_table(
        "mandates",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("donor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_donation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(10), server_default="active", nullable=False),
        sa.Column("next_charge_on", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount_paise >= 10000", name="ck_mandates_min_amount"),
        sa.CheckConstraint("status IN ('active','cancelled')", name="ck_mandates_status"),
        sa.ForeignKeyConstraint(["donor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.ForeignKeyConstraint(["first_donation_id"], ["donations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("first_donation_id"),
    )
    op.create_index("ix_mandates_due", "mandates", ["status", "next_charge_on"])
    op.create_index("ix_mandates_donor", "mandates", ["donor_id"])
    op.create_table(
        "callback_requests",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("phone", sa.String(10), nullable=False),
        sa.Column("name", sa.String(120), server_default="", nullable=False),
        sa.Column("scheme_code", sa.String(20), nullable=True),
        sa.Column("language", sa.String(2), server_default="hi", nullable=False),
        sa.Column("status", sa.String(10), server_default="new", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("status IN ('new','done')", name="ck_callbacks_status"),
        sa.CheckConstraint("language IN ('hi','en')", name="ck_callbacks_language"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_callbacks_status_created", "callback_requests", ["status", "created_at"])


def downgrade() -> None:
    op.drop_table("callback_requests")
    op.drop_table("mandates")
    op.drop_column("donations", "failure_reason")
    for column in ("documents_hi", "help_centre_hi", "how_to_apply_hi", "who_can_apply_hi"):
        op.drop_column("schemes", column)
