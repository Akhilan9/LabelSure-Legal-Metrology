"""Create Phase 4 image_processing_results table."""
from alembic import op
import sqlalchemy as sa

revision = "0003_image_quality"
down_revision = "0002_inspections"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "image_processing_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "inspection_image_id",
            sa.String(36),
            sa.ForeignKey("inspection_images.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("channels", sa.Integer(), nullable=True),
        sa.Column("blur_score", sa.Float(), nullable=True),
        sa.Column("brightness_score", sa.Float(), nullable=True),
        sa.Column("contrast_score", sa.Float(), nullable=True),
        sa.Column("glare_score", sa.Float(), nullable=True),
        sa.Column(
            "quality_status",
            sa.Enum(
                "PENDING",
                "GOOD",
                "ACCEPTABLE",
                "POOR",
                "UNREADABLE",
                "PROCESSING_FAILED",
                name="quality_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("quality_flags", sa.JSON(), nullable=False),
        sa.Column("derived_storage_path", sa.String(500), nullable=True),
        sa.Column("derived_filename", sa.String(255), nullable=True),
        sa.Column("derived_sha256", sa.String(64), nullable=True),
        sa.Column("processing_version", sa.String(32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_image_processing_results_inspection_image_id", "image_processing_results", ["inspection_image_id"], unique=True)
    op.create_index("ix_image_processing_results_quality_status", "image_processing_results", ["quality_status"])


def downgrade():
    op.drop_index("ix_image_processing_results_quality_status", table_name="image_processing_results")
    op.drop_index("ix_image_processing_results_inspection_image_id", table_name="image_processing_results")
    op.drop_table("image_processing_results")
