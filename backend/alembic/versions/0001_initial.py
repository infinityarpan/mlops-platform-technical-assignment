"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "models",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "model_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(128), sa.ForeignKey("models.id"), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("framework", sa.String(128), nullable=True),
        sa.Column("algorithm", sa.String(128), nullable=True),
        sa.Column("artifact_uri", sa.String(512), nullable=False),
        sa.Column("training_data_ref", sa.String(512), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("extra_metadata", sa.JSON(), nullable=True),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("lifecycle_stage", sa.String(32), nullable=False),
        sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("model_id", "version", name="uq_model_version"),
    )
    op.create_table(
        "deployments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(128), sa.ForeignKey("models.id"), nullable=False),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("previous_deployment_id", sa.String(36), nullable=True),
        sa.Column("failure_reason", sa.String(255), nullable=True),
        sa.Column("failure_class", sa.String(64), nullable=True),
        sa.Column("simulate_failure", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("idempotency_key", name="uq_idempotency_key"),
    )
    op.create_index(
        "uq_active_deployment_per_env",
        "deployments",
        ["model_id", "environment"],
        unique=True,
        sqlite_where=sa.text("status IN ('REQUESTED','VALIDATING','DEPLOYING')"),
        postgresql_where=sa.text("status IN ('REQUESTED','VALIDATING','DEPLOYING')"),
    )
    op.create_table(
        "deployment_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("deployment_id", sa.String(36), sa.ForeignKey("deployments.id"), nullable=False),
        sa.Column("event", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "metric_samples",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_id", sa.String(128), sa.ForeignKey("models.id"), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("throughput_rpm", sa.Float(), nullable=False),
        sa.Column("error_rate", sa.Float(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("drift_score", sa.Float(), nullable=False),
        sa.Column("availability", sa.Float(), nullable=False),
        sa.Column("last_successful_inference", sa.DateTime(timezone=True), nullable=True),
        sa.Column("monitoring_status", sa.String(32), nullable=False),
    )
    op.create_index("ix_metrics_model_ts", "metric_samples", ["model_id", "timestamp"])


def downgrade() -> None:
    op.drop_table("metric_samples")
    op.drop_table("deployment_events")
    op.drop_table("deployments")
    op.drop_table("model_versions")
    op.drop_table("models")
