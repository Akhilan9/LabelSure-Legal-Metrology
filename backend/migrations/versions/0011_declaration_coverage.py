"""Additional evidence-linked expiry, dimension and seller declarations."""
from alembic import op
from app.models.extraction import DeclarationType
revision='0011_declaration_coverage'
down_revision='0010_single_inspector'
branch_labels=None
depends_on=None

def upgrade():
    values=', '.join("'"+item.value+"'" for item in DeclarationType)
    with op.batch_alter_table('declaration_candidates') as batch:
        batch.drop_constraint('declaration_type',type_='check')
        batch.create_check_constraint('declaration_type',f'declaration_type IN ({values})')

def downgrade():
    raise RuntimeError('Export added declaration evidence before downgrading; evidence is never silently deleted.')
