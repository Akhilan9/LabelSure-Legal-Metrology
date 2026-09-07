"""Phase 6 declaration extraction; additive migration from OCR."""
from alembic import op
import sqlalchemy as sa
revision = "0005_extraction"
down_revision = "0004_ocr"
branch_labels = None
depends_on = None

def fk(name, target, nullable=False):
    return sa.Column(name, sa.String(36), sa.ForeignKey(target, ondelete="CASCADE"), nullable=nullable)

def enum(name, *values):
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)

def upgrade():
    op.create_table("extraction_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        fk("inspection_id", "inspections.id"),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", enum("extraction_status", "PENDING", "PROCESSING", "SUCCESS", "PARTIAL", "FAILED"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("candidate_count", sa.Integer, nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("warnings", sa.JSON, nullable=False),
        sa.UniqueConstraint("inspection_id", "version", "input_fingerprint", name="uq_extraction_input"))
    op.create_table("declaration_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        fk("extraction_run_id", "extraction_runs.id"),
        fk("inspection_id", "inspections.id"),
        sa.Column("declaration_type", enum("declaration_type",
            "COMMON_PRODUCT_NAME", "MANUFACTURER_NAME", "MANUFACTURER_ADDRESS", "PACKER_NAME", "PACKER_ADDRESS",
            "IMPORTER_NAME", "IMPORTER_ADDRESS", "NET_QUANTITY", "MRP", "MONTH_YEAR", "COUNTRY_OF_ORIGIN",
            "CONSUMER_CARE_NAME", "CONSUMER_CARE_ADDRESS", "CONSUMER_CARE_PHONE", "CONSUMER_CARE_EMAIL",
            "BARCODE_OR_GTIN", "UNIT_SALE_PRICE", "OTHER"), nullable=False),
        sa.Column("raw_value", sa.Text, nullable=False),
        sa.Column("normalized_value", sa.Text, nullable=False),
        sa.Column("structured_value", sa.JSON, nullable=False),
        fk("source_ocr_run_id", "ocr_runs.id"),
        fk("source_ocr_block_id", "ocr_blocks.id"),
        fk("source_image_id", "inspection_images.id"),
        sa.Column("panel_type", sa.String(32)),
        sa.Column("confidence_score", sa.Float, nullable=False),
        sa.Column("confidence_factors", sa.JSON, nullable=False),
        sa.Column("extraction_method", enum("extraction_method", "REGEX", "KEYWORD_CONTEXT", "SPATIAL_CONTEXT", "MULTI_BLOCK", "MANUAL", "OPTIONAL_LLM"), nullable=False),
        sa.Column("is_primary", sa.Boolean, nullable=False),
        sa.Column("needs_review", sa.Boolean, nullable=False),
        sa.Column("review_status", enum("declaration_review_status", "AUTO_EXTRACTED", "NEEDS_REVIEW", "VERIFIED", "REJECTED"), nullable=False),
        sa.Column("review_reasons", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("declaration_candidate_sources",
        fk("candidate_id", "declaration_candidates.id"),
        fk("ocr_block_id", "ocr_blocks.id"),
        sa.Column("sequence_order", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("candidate_id", "ocr_block_id"))
    for table, columns in {
        "extraction_runs": ["inspection_id"],
        "declaration_candidates": ["extraction_run_id", "inspection_id", "source_ocr_run_id", "source_image_id"]
    }.items():
        for column in columns:
            op.create_index("ix_" + table + "_" + column, table, [column])

def downgrade():
    op.drop_table("declaration_candidate_sources")
    op.drop_table("declaration_candidates")
    op.drop_table("extraction_runs")

