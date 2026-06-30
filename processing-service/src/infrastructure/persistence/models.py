from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProcessingRuleModel(Base):
    __tablename__ = "processing_rules"
    __table_args__ = (
        sa.CheckConstraint(
            "operator IN ('>', '>=', '<', '<=', '==')",
            name="ck_processing_rules_operator",
        ),
        {"schema": "processing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    metric: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    operator: Mapped[str] = mapped_column(sa.String(4), nullable=False)
    threshold: Mapped[float] = mapped_column(sa.Double(), nullable=False)
    severity: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    alert_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    message_template: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.true()
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )


class ProcessedObservationModel(Base):
    __tablename__ = "processed_observations"
    __table_args__ = (
        sa.UniqueConstraint("raw_observation_id", name="uq_processed_observations_raw_id"),
        {"schema": "processing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    raw_observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    temperature_c: Mapped[float | None] = mapped_column(sa.Double(), nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(sa.Double(), nullable=True)
    wind_speed_kmh: Mapped[float | None] = mapped_column(sa.Double(), nullable=True)
    precipitation_mm: Mapped[float | None] = mapped_column(sa.Double(), nullable=True)
    weather_code: Mapped[int | None] = mapped_column(sa.Integer(), nullable=True)
    heat_index_c: Mapped[float | None] = mapped_column(sa.Double(), nullable=True)
    wind_chill_c: Mapped[float | None] = mapped_column(sa.Double(), nullable=True)
    feels_like_c: Mapped[float | None] = mapped_column(sa.Double(), nullable=True)
    severity_score: Mapped[int] = mapped_column(
        sa.Integer(),
        nullable=False,
        server_default=sa.text("0"),
    )
    observed_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    processed_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )


class AlertModel(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        sa.Index("ix_alerts_severity", "severity"),
        sa.Index("ix_alerts_acknowledged", "acknowledged"),
        {"schema": "processing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    processed_observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("processing.processed_observations.id"),
        nullable=False,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("processing.processing_rules.id"),
        nullable=False,
    )
    alert_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    severity: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    message: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    acknowledged: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.false()
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    acknowledged_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )


class WatermarkModel(Base):
    __tablename__ = "watermarks"
    __table_args__ = (
        sa.UniqueConstraint("source", name="uq_watermarks_source"),
        {"schema": "processing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    source: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True)
    last_ingested_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
