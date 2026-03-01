"""add_organization_multi_tenancy

Revision ID: c0a1b2d3e4f5
Revises: 09eda1c0fb44
Create Date: 2026-03-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0a1b2d3e4f5'
down_revision = '09eda1c0fb44'
branch_labels = None
depends_on = None


def upgrade():
    # === 1. Create organizations table ===
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
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)

    # === 2. Create organization_memberships table ===
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
    op.create_index('ix_org_memberships_user_id', 'organization_memberships', ['user_id'])
    op.create_index('ix_org_memberships_org_id', 'organization_memberships', ['org_id'])

    # === 3. Add is_superadmin to users ===
    op.add_column('users', sa.Column('is_superadmin', sa.Boolean(), nullable=False, server_default='false'))

    # === 4. Add org_id (NULLABLE) to bands ===
    op.add_column('bands', sa.Column('org_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_bands_org_id', 'bands', 'organizations', ['org_id'], ['id'])
    op.create_index('ix_bands_org_id', 'bands', ['org_id'])

    # === 5. Add org_id (NULLABLE) to venues ===
    op.add_column('venues', sa.Column('org_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_venues_org_id', 'venues', 'organizations', ['org_id'], ['id'])
    op.create_index('ix_venues_org_id', 'venues', ['org_id'])

    # === 6. Add org_id (NULLABLE) to subscriptions ===
    op.add_column('subscriptions', sa.Column('org_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_subscriptions_org_id', 'subscriptions', 'organizations', ['org_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_subscriptions_org_id', 'subscriptions', ['org_id'], unique=True)

    # === 7. Make user_id nullable on subscriptions (backward compat) ===
    op.alter_column('subscriptions', 'user_id', existing_type=sa.Integer(), nullable=True)

    # === 8. Data migration: create default org, assign existing data ===
    # This is handled by `flask setup-org` CLI command for safety.
    # In production, run: flask setup-org
    # The command creates a default org and assigns all bands/venues/users to it,
    # then makes org_id NOT NULL.


def downgrade():
    # === Reverse: remove org_id columns ===
    op.alter_column('subscriptions', 'user_id', existing_type=sa.Integer(), nullable=False)

    op.drop_index('ix_subscriptions_org_id', table_name='subscriptions')
    op.drop_constraint('fk_subscriptions_org_id', 'subscriptions', type_='foreignkey')
    op.drop_column('subscriptions', 'org_id')

    op.drop_index('ix_venues_org_id', table_name='venues')
    op.drop_constraint('fk_venues_org_id', 'venues', type_='foreignkey')
    op.drop_column('venues', 'org_id')

    op.drop_index('ix_bands_org_id', table_name='bands')
    op.drop_constraint('fk_bands_org_id', 'bands', type_='foreignkey')
    op.drop_column('bands', 'org_id')

    op.drop_column('users', 'is_superadmin')

    op.drop_index('ix_org_memberships_org_id', table_name='organization_memberships')
    op.drop_index('ix_org_memberships_user_id', table_name='organization_memberships')
    op.drop_table('organization_memberships')

    # Drop enum type for PostgreSQL
    op.execute('DROP TYPE IF EXISTS orgrole')

    op.drop_index('ix_organizations_slug', table_name='organizations')
    op.drop_table('organizations')
