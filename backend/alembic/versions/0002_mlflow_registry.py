"""drop postgres model registry; mlflow is source of truth

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("metric_samples_model_id_fkey", "metric_samples", type_="foreignkey")
    op.drop_constraint("deployments_version_id_fkey", "deployments", type_="foreignkey")
    op.drop_constraint("deployments_model_id_fkey", "deployments", type_="foreignkey")
    op.alter_column("deployments", "version_id", existing_type=sa.String(36), type_=sa.String(160))
    op.drop_table("model_versions")
    op.drop_table("models")


def downgrade() -> None:
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
    op.alter_column("deployments", "version_id", existing_type=sa.String(160), type_=sa.String(36))
    op.create_foreign_key("deployments_model_id_fkey", "deployments", "models", ["model_id"], ["id"])
    op.create_foreign_key("deployments_version_id_fkey", "deployments", "model_versions", ["version_id"], ["id"])
    op.create_foreign_key("metric_samples_model_id_fkey", "metric_samples", "models", ["model_id"], ["id"])
