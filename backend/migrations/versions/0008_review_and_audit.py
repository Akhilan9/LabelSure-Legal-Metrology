"""Phase 10 human review, overrides, corrections, and audit trail."""
from alembic import op
import sqlalchemy as sa

revision = "0008_review_and_audit"
down_revision = "0007_rules"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'inspection_reviews',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('inspection_id', sa.String(length=36), nullable=False),
        sa.Column('reviewer_user_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'FINALIZED', 'REOPENED', name='review_status', native_enum=False, create_constraint=True), nullable=False),
        sa.Column('final_compliance_status', sa.Enum('COMPLIANT', 'NON_COMPLIANT', 'CONDITIONAL_COMPLIANCE', 'REJECTED', 'UNCERTAIN', name='review_compliance_status', native_enum=False, create_constraint=False), nullable=True),
        sa.Column('summary_notes', sa.Text(), nullable=True),
        sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inspection_reviews_inspection_id'), 'inspection_reviews', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_inspection_reviews_reviewer_user_id'), 'inspection_reviews', ['reviewer_user_id'], unique=False)

    op.create_table(
        'rule_review_decisions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('review_id', sa.String(length=36), nullable=False),
        sa.Column('rule_id', sa.String(length=64), nullable=False),
        sa.Column('rule_key', sa.String(length=64), nullable=False),
        sa.Column('original_verdict', sa.Enum('PASS', 'FAIL', 'UNCERTAIN', 'NOT_APPLICABLE', name='rule_review_original_verdict', native_enum=False, create_constraint=True), nullable=False),
        sa.Column('final_verdict', sa.Enum('PASS', 'FAIL', 'UNCERTAIN', 'NOT_APPLICABLE', name='rule_review_final_verdict', native_enum=False, create_constraint=True), nullable=False),
        sa.Column('is_overridden', sa.Boolean(), nullable=False),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['inspection_reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rule_review_decisions_review_id'), 'rule_review_decisions', ['review_id'], unique=False)

    op.create_table(
        'declaration_corrections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('review_id', sa.String(length=36), nullable=False),
        sa.Column('candidate_id', sa.String(length=36), nullable=True),
        sa.Column('declaration_type', sa.String(length=64), nullable=False),
        sa.Column('original_raw_value', sa.Text(), nullable=True),
        sa.Column('original_normalized_value', sa.Text(), nullable=True),
        sa.Column('corrected_value', sa.Text(), nullable=False),
        sa.Column('action', sa.Enum('CONFIRMED', 'CORRECTED', 'REJECTED', 'MANUALLY_ADDED', name='declaration_correction_action', native_enum=False, create_constraint=True), nullable=False),
        sa.Column('correction_reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['declaration_candidates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['review_id'], ['inspection_reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_declaration_corrections_candidate_id'), 'declaration_corrections', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_declaration_corrections_review_id'), 'declaration_corrections', ['review_id'], unique=False)

    op.create_table(
        'ocr_corrections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('review_id', sa.String(length=36), nullable=False),
        sa.Column('ocr_block_id', sa.String(length=36), nullable=True),
        sa.Column('inspection_image_id', sa.String(length=36), nullable=True),
        sa.Column('original_text', sa.Text(), nullable=True),
        sa.Column('corrected_text', sa.Text(), nullable=False),
        sa.Column('action', sa.Enum('CONFIRMED', 'CORRECTED', 'REJECTED', 'MANUALLY_ADDED', name='ocr_correction_action', native_enum=False, create_constraint=True), nullable=False),
        sa.Column('correction_reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspection_image_id'], ['inspection_images.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ocr_block_id'], ['ocr_blocks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['review_id'], ['inspection_reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ocr_corrections_inspection_image_id'), 'ocr_corrections', ['inspection_image_id'], unique=False)
    op.create_index(op.f('ix_ocr_corrections_ocr_block_id'), 'ocr_corrections', ['ocr_block_id'], unique=False)
    op.create_index(op.f('ix_ocr_corrections_review_id'), 'ocr_corrections', ['review_id'], unique=False)

    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('inspection_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=True),
        sa.Column('before_state', sa.JSON(), nullable=True),
        sa.Column('after_state', sa.JSON(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_events_action'), 'audit_events', ['action'], unique=False)
    op.create_index(op.f('ix_audit_events_created_at'), 'audit_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_events_entity_type'), 'audit_events', ['entity_type'], unique=False)
    op.create_index(op.f('ix_audit_events_inspection_id'), 'audit_events', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_audit_events_user_id'), 'audit_events', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_audit_events_user_id'), table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_inspection_id'), table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_entity_type'), table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_created_at'), table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_action'), table_name='audit_events')
    op.drop_table('audit_events')

    op.drop_index(op.f('ix_ocr_corrections_review_id'), table_name='ocr_corrections')
    op.drop_index(op.f('ix_ocr_corrections_ocr_block_id'), table_name='ocr_corrections')
    op.drop_index(op.f('ix_ocr_corrections_inspection_image_id'), table_name='ocr_corrections')
    op.drop_table('ocr_corrections')

    op.drop_index(op.f('ix_declaration_corrections_review_id'), table_name='declaration_corrections')
    op.drop_index(op.f('ix_declaration_corrections_candidate_id'), table_name='declaration_corrections')
    op.drop_table('declaration_corrections')

    op.drop_index(op.f('ix_rule_review_decisions_review_id'), table_name='rule_review_decisions')
    op.drop_table('rule_review_decisions')

    op.drop_index(op.f('ix_inspection_reviews_reviewer_user_id'), table_name='inspection_reviews')
    op.drop_index(op.f('ix_inspection_reviews_inspection_id'), table_name='inspection_reviews')
    op.drop_table('inspection_reviews')
