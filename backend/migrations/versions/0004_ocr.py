"""Create Phase 5 ocr_runs and ocr_blocks tables."""
from alembic import op
import sqlalchemy as sa

revision = "0004_ocr"
down_revision = "0003_image_quality"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ocr_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "inspection_id",
            sa.String(36),
            sa.ForeignKey("inspections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "inspection_image_id",
            sa.String(36),
            sa.ForeignKey("inspection_images.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "image_processing_result_id",
            sa.String(36),
            sa.ForeignKey("image_processing_results.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("engine_name", sa.String(64), nullable=False),
        sa.Column("engine_version", sa.String(32), nullable=False),
        sa.Column("language_config", sa.String(32), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "PROCESSING",
                "SUCCESS",
                "PARTIAL",
                "FAILED",
                name="ocr_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("average_confidence", sa.Float(), nullable=True),
        sa.Column("block_count", sa.Integer(), nullable=False, default=0),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message_safe", sa.Text(), nullable=True),
        sa.Column("ocr_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ocr_runs_inspection_id", "ocr_runs", ["inspection_id"])
    op.create_index("ix_ocr_runs_inspection_image_id", "ocr_runs", ["inspection_image_id"])
    op.create_index("ix_ocr_runs_image_processing_result_id", "ocr_runs", ["image_processing_result_id"])
    op.create_index("ix_ocr_runs_status", "ocr_runs", ["status"])

    op.create_table(
        "ocr_blocks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "ocr_run_id",
            sa.String(36),
            sa.ForeignKey("ocr_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "inspection_id",
            sa.String(36),
            sa.ForeignKey("inspections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "inspection_image_id",
            sa.String(36),
            sa.ForeignKey("inspection_images.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("block_index", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "confidence_tier",
            sa.Enum(
                "GOOD",
                "REVIEW",
                "LOW",
                name="ocr_confidence_tier",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("polygon", sa.JSON(), nullable=False),
        sa.Column("bounding_box", sa.JSON(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("reading_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ocr_blocks_ocr_run_id", "ocr_blocks", ["ocr_run_id"])
    op.create_index("ix_ocr_blocks_inspection_id", "ocr_blocks", ["inspection_id"])
    op.create_index("ix_ocr_blocks_inspection_image_id", "ocr_blocks", ["inspection_image_id"])
    op.create_index("ix_ocr_blocks_confidence_tier", "ocr_blocks", ["confidence_tier"])
    op.create_index("ix_ocr_blocks_reading_order", "ocr_blocks", ["reading_order"])


def downgrade():
    op.drop_index("ix_ocr_blocks_reading_order", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_confidence_tier", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_inspection_image_id", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_inspection_id", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_ocr_run_id", table_name="ocr_blocks")
    op.drop_table("ocr_blocks")

    op.drop_index("ix_ocr_runs_status", table_name="ocr_runs")
    op.drop_index("ix_ocr_runs_image_processing_result_id", table_name="ocr_runs")
    op.drop_index("ix_ocr_runs_inspection_image_id", table_name="ocr_runs")
    op.drop_index("ix_ocr_runs_inspection_id", table_name="ocr_runs")
    op.drop_table("ocr_runs")
