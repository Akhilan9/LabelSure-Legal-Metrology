"""Phase 11 generated reports and snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "0009_reports"
down_revision = "0008_review_and_audit"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'generated_reports',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('inspection_id', sa.String(length=36), nullable=False),
        sa.Column('report_type', sa.Enum('SUMMARY', 'DETAILED', 'LEGAL_NOTICE', 'VIOLATION_EXPORT', name='report_type', native_enum=False, create_constraint=True), nullable=False),
        sa.Column('format', sa.Enum('PDF', 'JSON', 'CSV', name='report_format', native_enum=False, create_constraint=True), nullable=False),
        sa.Column('status', sa.Enum('GENERATED', 'FAILED', name='report_status', native_enum=False, create_constraint=True), nullable=False),
        sa.Column('content_sha256', sa.String(length=64), nullable=False),
        sa.Column('report_data', sa.JSON(), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=True),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_generated_reports_content_sha256'), 'generated_reports', ['content_sha256'], unique=False)
    op.create_index(op.f('ix_generated_reports_created_by_user_id'), 'generated_reports', ['created_by_user_id'], unique=False)
    op.create_index(op.f('ix_generated_reports_inspection_id'), 'generated_reports', ['inspection_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_generated_reports_inspection_id'), table_name='generated_reports')
    op.drop_index(op.f('ix_generated_reports_created_by_user_id'), table_name='generated_reports')
    op.drop_index(op.f('ix_generated_reports_content_sha256'), table_name='generated_reports')
    op.drop_table('generated_reports')
