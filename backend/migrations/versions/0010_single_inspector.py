"""Consolidate accounts into Inspector while preserving accounts and evidence."""
from alembic import op
import sqlalchemy as sa
revision = '0010_single_inspector'
down_revision = '0009_reports'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("UPDATE users SET role = 'INSPECTOR'")
    with op.batch_alter_table('users') as batch:
        batch.drop_constraint('user_role', type_='check')
        batch.create_check_constraint('user_role', "role IN ('INSPECTOR')")

def downgrade():
    with op.batch_alter_table('users') as batch:
        batch.drop_constraint('user_role', type_='check')
        batch.create_check_constraint('user_role', "role IN ('ADMIN', 'INSPECTOR', 'SUPERVISOR')")
