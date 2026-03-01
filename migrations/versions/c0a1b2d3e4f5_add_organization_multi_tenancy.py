"""add_organization_multi_tenancy

Revision ID: c0a1b2d3e4f5
Revises: 9e6304801c01
Create Date: 2026-03-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0a1b2d3e4f5'
down_revision = '9e6304801c01'
branch_labels = None
depends_on = None


def _table_exists(table_name):
    """Check if a table already exists (db.create_all() may have created it)."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:name"
    ), {'name': table_name})
    return result.fetchone() is not None


def _column_exists(table_name, column_name):
    """Check if a column already exists on a table."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table_name})"))
    columns = [row[1] for row in result.fetchall()]
    return column_name in columns


def _index_exists(index_name):
    """Check if an index already exists."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=:name"
    ), {'name': index_name})
    return result.fetchone() is not None


def upgrade():
    # === 1. Create organizations table (if not already created by db.create_all) ===
    if not _table_exists('organizations'):
        op.create_table(
            'organizations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('slug', sa.String(length=100), nullable=False),
            sa.Column('logo_path', sa.String(length=255), nullable=True),
            sa.Column('website', sa.String(length=255), nullable=True),
            sa.Column('phone', sa.String(length=30), nullable=True),
            sa.Column('email', sa.String(length=120), nullable=True),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('siret', sa.String(length=14), nullable=True),
            sa.Column('vat_number', sa.String(length=20), nullable=True),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
    if not _index_exists('ix_organizations_slug'):
        op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)

    # === 2. Create organization_memberships table ===
    if not _table_exists('organization_memberships'):
        op.create_table(
            'organization_memberships',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('role', sa.Enum('owner', 'admin', 'member', name='orgrole'), nullable=False),
            sa.Column('joined_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'org_id', name='uq_user_org'),
        )
    if not _index_exists('ix_org_memberships_user_id'):
        op.create_index('ix_org_memberships_user_id', 'organization_memberships', ['user_id'])
    if not _index_exists('ix_org_memberships_org_id'):
        op.create_index('ix_org_memberships_org_id', 'organization_memberships', ['org_id'])

    # === 3. Add is_superadmin to users ===
    if not _column_exists('users', 'is_superadmin'):
        op.add_column('users', sa.Column('is_superadmin', sa.Boolean(), nullable=False, server_default='false'))

    # === 4. Add org_id (NULLABLE) to bands ===
    if not _column_exists('bands', 'org_id'):
        op.add_column('bands', sa.Column('org_id', sa.Integer(), nullable=True))
    # SQLite doesn't enforce FK constraints added via ALTER, but keep for PostgreSQL compat
    if not _index_exists('ix_bands_org_id'):
        op.create_index('ix_bands_org_id', 'bands', ['org_id'])

    # === 5. Add org_id (NULLABLE) to venues ===
    if not _column_exists('venues', 'org_id'):
        op.add_column('venues', sa.Column('org_id', sa.Integer(), nullable=True))
    if not _index_exists('ix_venues_org_id'):
        op.create_index('ix_venues_org_id', 'venues', ['org_id'])

    # === 6. Add org_id (NULLABLE) to subscriptions ===
    if not _column_exists('subscriptions', 'org_id'):
        op.add_column('subscriptions', sa.Column('org_id', sa.Integer(), nullable=True))
    if not _index_exists('ix_subscriptions_org_id'):
        op.create_index('ix_subscriptions_org_id', 'subscriptions', ['org_id'], unique=True)

    # === 7. Data migration: create default org, assign existing data ===
    # Automatically populate org for existing data
    conn = op.get_bind()

    # Check if there's already an org (idempotent)
    org_count = conn.execute(sa.text("SELECT COUNT(*) FROM organizations")).scalar()
    if org_count == 0:
        # Get the first user to be the org creator
        first_user = conn.execute(sa.text(
            "SELECT id, first_name, last_name, email FROM users ORDER BY id LIMIT 1"
        )).fetchone()

        if first_user:
            from datetime import datetime
            now = datetime.utcnow().isoformat()

            # Create default organization
            conn.execute(sa.text(
                "INSERT INTO organizations (name, slug, email, created_by_id, created_at, updated_at) "
                "VALUES (:name, :slug, :email, :created_by_id, :created_at, :updated_at)"
            ), {
                'name': f"Équipe de {first_user[1]} {first_user[2]}",
                'slug': 'default-org',
                'email': first_user[3],
                'created_by_id': first_user[0],
                'created_at': now,
                'updated_at': now,
            })

            # Get the org ID
            org_id = conn.execute(sa.text("SELECT id FROM organizations WHERE slug='default-org'")).scalar()

            # Assign all bands and venues to this org
            conn.execute(sa.text("UPDATE bands SET org_id = :org_id"), {'org_id': org_id})
            conn.execute(sa.text("UPDATE venues SET org_id = :org_id"), {'org_id': org_id})

            # Create membership for all existing users (first user = OWNER, rest = MEMBER)
            users = conn.execute(sa.text("SELECT id FROM users ORDER BY id")).fetchall()
            for user_row in users:
                role = 'owner' if user_row[0] == first_user[0] else 'member'
                conn.execute(sa.text(
                    "INSERT INTO organization_memberships (user_id, org_id, role, joined_at) "
                    "VALUES (:user_id, :org_id, :role, :joined_at)"
                ), {
                    'user_id': user_row[0],
                    'org_id': org_id,
                    'role': role,
                    'joined_at': now,
                })

            # Link existing subscription to org (if any)
            conn.execute(sa.text(
                "UPDATE subscriptions SET org_id = :org_id WHERE org_id IS NULL"
            ), {'org_id': org_id})


def downgrade():
    # === Reverse: remove org_id columns ===
    op.drop_index('ix_subscriptions_org_id', table_name='subscriptions')
    op.drop_column('subscriptions', 'org_id')

    op.drop_index('ix_venues_org_id', table_name='venues')
    op.drop_column('venues', 'org_id')

    op.drop_index('ix_bands_org_id', table_name='bands')
    op.drop_column('bands', 'org_id')

    op.drop_column('users', 'is_superadmin')

    op.drop_index('ix_org_memberships_org_id', table_name='organization_memberships')
    op.drop_index('ix_org_memberships_user_id', table_name='organization_memberships')
    op.drop_table('organization_memberships')

    # Drop enum type for PostgreSQL
    op.execute('DROP TYPE IF EXISTS orgrole')

    op.drop_index('ix_organizations_slug', table_name='organizations')
    op.drop_table('organizations')
