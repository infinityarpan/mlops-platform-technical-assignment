"""drop unused metric_samples table

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_metrics_model_ts", table_name="metric_samples")
    op.drop_table("metric_samples")


def downgrade() -> None:
    op.create_table(
        "metric_samples",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_id", sa.String(128), nullable=False),
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
