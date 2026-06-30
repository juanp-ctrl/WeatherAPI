"""Initial ingestion schema

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
    op.execute("CREATE SCHEMA IF NOT EXISTS ingestion")

    op.create_table(
        "locations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("latitude", sa.Double(), nullable=False),
        sa.Column("longitude", sa.Double(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
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
        schema="ingestion",
    )

    op.create_table(
        "raw_observations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "location_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ingestion.locations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("temperature_c", sa.Double(), nullable=True),
        sa.Column("humidity_pct", sa.Double(), nullable=True),
        sa.Column("wind_speed_kmh", sa.Double(), nullable=True),
        sa.Column("precipitation_mm", sa.Double(), nullable=True),
        sa.Column("weather_code", sa.Integer(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "location_id",
            "observed_at",
            name="uq_raw_observations_location_observed",
        ),
        schema="ingestion",
    )

    op.create_index(
        "ix_raw_observations_location_id",
        "raw_observations",
        ["location_id"],
        schema="ingestion",
    )
    op.create_index(
        "ix_raw_observations_observed_at",
        "raw_observations",
        ["observed_at"],
        schema="ingestion",
    )
    op.create_index(
        "ix_raw_observations_ingested_at",
        "raw_observations",
        ["ingested_at"],
        schema="ingestion",
    )


def downgrade() -> None:
    op.drop_index("ix_raw_observations_ingested_at", table_name="raw_observations", schema="ingestion")
    op.drop_index("ix_raw_observations_observed_at", table_name="raw_observations", schema="ingestion")
    op.drop_index("ix_raw_observations_location_id", table_name="raw_observations", schema="ingestion")
    op.drop_table("raw_observations", schema="ingestion")
    op.drop_table("locations", schema="ingestion")
