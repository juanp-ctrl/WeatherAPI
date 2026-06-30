"""Initial processing schema

Revision ID: 0001
Revises:
Create Date: 2026-06-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS processing")

    op.create_table(
        "processing_rules",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("operator", sa.String(4), nullable=False),
        sa.Column("threshold", sa.Double(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("message_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "operator IN ('>', '>=', '<', '<=', '==')",
            name="ck_processing_rules_operator",
        ),
        schema="processing",
    )

    op.create_table(
        "processed_observations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("raw_observation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", UUID(as_uuid=True), nullable=False),
        sa.Column("temperature_c", sa.Double(), nullable=True),
        sa.Column("humidity_pct", sa.Double(), nullable=True),
        sa.Column("wind_speed_kmh", sa.Double(), nullable=True),
        sa.Column("precipitation_mm", sa.Double(), nullable=True),
        sa.Column("weather_code", sa.Integer(), nullable=True),
        sa.Column("heat_index_c", sa.Double(), nullable=True),
        sa.Column("wind_chill_c", sa.Double(), nullable=True),
        sa.Column("feels_like_c", sa.Double(), nullable=True),
        sa.Column(
            "severity_score",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "raw_observation_id", name="uq_processed_observations_raw_id"
        ),
        schema="processing",
    )

    op.create_table(
        "alerts",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "processed_observation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("processing.processed_observations.id"),
            nullable=False,
        ),
        sa.Column(
            "rule_id",
            UUID(as_uuid=True),
            sa.ForeignKey("processing.processing_rules.id"),
            nullable=False,
        ),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        schema="processing",
    )

    op.create_index("ix_alerts_severity", "alerts", ["severity"], schema="processing")
    op.create_index(
        "ix_alerts_acknowledged", "alerts", ["acknowledged"], schema="processing"
    )

    op.create_table(
        "watermarks",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("source", name="uq_watermarks_source"),
        schema="processing",
    )


def downgrade() -> None:
    op.drop_table("watermarks", schema="processing")
    op.drop_index("ix_alerts_acknowledged", table_name="alerts", schema="processing")
    op.drop_index("ix_alerts_severity", table_name="alerts", schema="processing")
    op.drop_table("alerts", schema="processing")
    op.drop_table("processed_observations", schema="processing")
    op.drop_table("processing_rules", schema="processing")
