"""SQLAlchemy ORM models — bi-temporal schema for PUMA benchmark data."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Run(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    spec_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    spec_yaml: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running|done|error

    predictions: Mapped[list[Prediction]] = relationship(back_populates="run", cascade="all")
    metrics: Mapped[list[Metric]] = relationship(back_populates="run", cascade="all")
    emissions: Mapped[list[Emission]] = relationship(back_populates="run", cascade="all")
    profile_snapshot: Mapped[ProfileSnapshot | None] = relationship(
        back_populates="run", uselist=False, cascade="all"
    )


class Instance(Base):
    __tablename__ = "instances"

    instance_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    gold_label: Mapped[str] = mapped_column(String(128), nullable=False)

    __table_args__ = (UniqueConstraint("dataset", "source_id", name="uq_dataset_source"),)

    predictions: Mapped[list[Prediction]] = relationship(back_populates="instance")


class Prediction(Base):
    __tablename__ = "predictions"

    pred_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False)
    instance_id: Mapped[str] = mapped_column(ForeignKey("instances.instance_id"), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    logprobs_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    perturbation: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seed: Mapped[int] = mapped_column(Integer, default=42)

    run: Mapped[Run] = relationship(back_populates="predictions")
    instance: Mapped[Instance] = relationship(back_populates="predictions")


class Metric(Base):
    __tablename__ = "metrics"

    metric_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)  # global|per_model|per_group
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    strategy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    subgroup: Mapped[str | None] = mapped_column(String(128), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped[Run] = relationship(back_populates="metrics")


class Emission(Base):
    __tablename__ = "emissions"

    emission_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False)
    kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    co2_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpu_energy: Mapped[float | None] = mapped_column(Float, nullable=True)
    gpu_energy: Mapped[float | None] = mapped_column(Float, nullable=True)
    ram_energy: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped[Run] = relationship(back_populates="emissions")


class ProfileSnapshot(Base):
    __tablename__ = "profile_snapshots"

    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False, unique=True)
    os: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cpu: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ram_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    gpu: Mapped[str | None] = mapped_column(String(128), nullable=True)
    vram_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    ollama_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    puma_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    run: Mapped[Run] = relationship(back_populates="profile_snapshot")
