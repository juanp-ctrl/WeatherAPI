from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


class Base(DeclarativeBase):
    pass


class LocationModel(Base):
    __tablename__ = "locations"
    __table_args__ = {"schema": "ingestion"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(sa.Double(), nullable=False)
    longitude: Mapped[float] = mapped_column(sa.Double(), nullable=False)
    timezone: Mapped[str] = mapped_column(
        sa.String(64), nullable=False, server_default="UTC"
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.true()
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )


class RawObservationModel(Base):
    __tablename__ = "raw_observations"
    __table_args__ = (
        sa.UniqueConstraint(
            "location_id", "observed_at", name="uq_raw_observations_location_observed"
        ),
        sa.Index("ix_raw_observations_location_id", "location_id"),
        sa.Index("ix_raw_observations_observed_at", "observed_at"),
        sa.Index("ix_raw_observations_ingested_at", "ingested_at"),
        {"schema": "ingestion"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("ingestion.locations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    temperature_c: Mapped[float | None] = mapped_column(sa.Double(), nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(sa.Double(), nullable=True)
    wind_speed_kmh: Mapped[float | None] = mapped_column(sa.Double(), nullable=True)
    precipitation_mm: Mapped[float | None] = mapped_column(sa.Double(), nullable=True)
    weather_code: Mapped[int | None] = mapped_column(sa.Integer(), nullable=True)
    observed_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    ingested_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
