"""Create Phase 3 inspections and inspection_images tables."""
from alembic import op
import sqlalchemy as sa

revision = "0002_inspections"
down_revision = "0001_users"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inspections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("inspection_code", sa.String(32), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_to_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT", "EVIDENCE_UPLOADED", "READY_FOR_ANALYSIS", "PROCESSING",
                "REVIEW_REQUIRED", "COMPLIANT", "NON_COMPLIANT", "UNCERTAIN", "FINALIZED",
                name="inspection_status", native_enum=False, create_constraint=True
            ),
            nullable=False,
        ),
        sa.Column("product_name", sa.String(255), nullable=True),
        sa.Column("brand_name", sa.String(255), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("package_type", sa.String(100), nullable=True),
        sa.Column(
            "import_status",
            sa.Enum("UNKNOWN", "DOMESTIC", "IMPORTED", name="import_status", native_enum=False, create_constraint=True),
            nullable=True,
        ),
        sa.Column("barcode", sa.String(64), nullable=True),
        sa.Column("manufacturer_name", sa.String(255), nullable=True),
        sa.Column("packer_name", sa.String(255), nullable=True),
        sa.Column("importer_name", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_inspections_inspection_code", "inspections", ["inspection_code"], unique=True)
    op.create_index("ix_inspections_created_by_user_id", "inspections", ["created_by_user_id"])
    op.create_index("ix_inspections_assigned_to_user_id", "inspections", ["assigned_to_user_id"])
    op.create_index("ix_inspections_status", "inspections", ["status"])
    op.create_index("ix_inspections_barcode", "inspections", ["barcode"])

    op.create_table(
        "inspection_images",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("inspection_id", sa.String(36), sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column(
            "panel_type",
            sa.Enum(
                "FRONT", "BACK", "LEFT", "RIGHT", "TOP", "BOTTOM",
                "DECLARATION_PANEL", "MRP_PANEL", "OTHER",
                name="panel_type", native_enum=False, create_constraint=True
            ),
            nullable=False,
        ),
        sa.Column("upload_order", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("quality_status", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inspection_images_inspection_id", "inspection_images", ["inspection_id"])
    op.create_index("ix_inspection_images_uploaded_by_user_id", "inspection_images", ["uploaded_by_user_id"])


def downgrade():
    op.drop_index("ix_inspection_images_uploaded_by_user_id", table_name="inspection_images")
    op.drop_index("ix_inspection_images_inspection_id", table_name="inspection_images")
    op.drop_table("inspection_images")

    op.drop_index("ix_inspections_barcode", table_name="inspections")
    op.drop_index("ix_inspections_status", table_name="inspections")
    op.drop_index("ix_inspections_assigned_to_user_id", table_name="inspections")
    op.drop_index("ix_inspections_created_by_user_id", table_name="inspections")
    op.drop_index("ix_inspections_inspection_code", table_name="inspections")
    op.drop_table("inspections")
