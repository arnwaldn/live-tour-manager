"""add_org_id_to_system_settings

Revision ID: a1b2c3d4e5f7
Revises: c0a1b2d3e4f5
Create Date: 2026-03-02 12:00:00.000000

Adds org_id to system_settings for per-organization configuration.
Replaces global unique constraint on key with composite unique on (org_id, key).
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f7'
down_revision = 'c0a1b2d3e4f5'
branch_labels = None
depends_on = None


def _table_exists(table_name):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def _column_exists(table_name, column_name):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def _index_exists(index_name):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for table_name in inspector.get_table_names():
        indexes = inspector.get_indexes(table_name)
        if any(idx['name'] == index_name for idx in indexes):
            return True
    return False


def _constraint_exists(table_name, constraint_name):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    uniques = inspector.get_unique_constraints(table_name)
    return any(c['name'] == constraint_name for c in uniques)


def upgrade():
    if not _table_exists('system_settings'):
        return

    # 1. Add org_id column (nullable — NULL means global/default)
    if not _column_exists('system_settings', 'org_id'):
        op.add_column('system_settings',
                       sa.Column('org_id', sa.Integer(),
                                 sa.ForeignKey('organizations.id'), nullable=True))

    # 2. Drop old unique constraint on key alone
    #    SQLite doesn't support DROP CONSTRAINT, so we handle both dialects
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'postgresql':
        # PostgreSQL: drop the old unique index/constraint on key
        op.execute("""
            DO $$
            BEGIN
                -- Drop unique constraint if exists
                IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'system_settings_key_key') THEN
                    ALTER TABLE system_settings DROP CONSTRAINT system_settings_key_key;
                END IF;
            END $$;
        """)
        # Drop index if exists (created by unique=True)
        if _index_exists('ix_system_settings_key'):
            op.drop_index('ix_system_settings_key', table_name='system_settings')

        # 3. Create composite unique index
        if not _index_exists('uq_system_settings_org_key'):
            op.execute("""
                CREATE UNIQUE INDEX uq_system_settings_org_key
                ON system_settings (COALESCE(org_id, 0), key)
            """)
    else:
        # SQLite: can't alter constraints, but we can create the new index
        # The old unique constraint is baked into the table schema on SQLite
        # We'll just add our composite index — SQLite will enforce both
        # (the old one is fine for dev since we only have one org)
        if not _index_exists('uq_system_settings_org_key'):
            op.create_index('uq_system_settings_org_key', 'system_settings',
                            ['org_id', 'key'], unique=True)

    # 4. Index on org_id for faster lookups
    if not _index_exists('ix_system_settings_org_id'):
        op.create_index('ix_system_settings_org_id', 'system_settings', ['org_id'])

    # 5. Data migration: assign existing settings to default org
    conn = op.get_bind()
    default_org = conn.execute(
        sa.text("SELECT id FROM organizations WHERE slug = 'default-org' LIMIT 1")
    ).fetchone()

    if default_org:
        conn.execute(
            sa.text("UPDATE system_settings SET org_id = :org_id WHERE org_id IS NULL"),
            {'org_id': default_org[0]}
        )


def downgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name

    # Remove composite index
    if _index_exists('uq_system_settings_org_key'):
        op.drop_index('uq_system_settings_org_key', table_name='system_settings')

    if _index_exists('ix_system_settings_org_id'):
        op.drop_index('ix_system_settings_org_id', table_name='system_settings')

    # Clear org_id values before dropping column
    conn.execute(sa.text("UPDATE system_settings SET org_id = NULL"))

    if dialect == 'postgresql':
        op.drop_column('system_settings', 'org_id')
        # Recreate original unique constraint
        op.create_index('ix_system_settings_key', 'system_settings', ['key'], unique=True)
    else:
        # SQLite: can't drop columns easily, just remove the column
        op.drop_column('system_settings', 'org_id')
