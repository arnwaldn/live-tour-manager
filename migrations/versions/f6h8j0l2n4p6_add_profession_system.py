"""Add profession system with access levels and labels

Revision ID: f6h8j0l2n4p6
Revises: 5fc84d517d83
Create Date: 2026-01-25 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'f6h8j0l2n4p6'
down_revision = '5fc84d517d83'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create labels table
    op.create_table('labels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('code', sa.String(50), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_labels_code', 'labels', ['code'], unique=True)

    # 2. Create professions table
    op.create_table('professions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name_fr', sa.String(100), nullable=False),
        sa.Column('name_en', sa.String(100), nullable=False),
        sa.Column('category', sa.String(20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('default_access_level', sa.String(20), default='STAFF'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_professions_code', 'professions', ['code'], unique=True)
    op.create_index('ix_professions_category', 'professions', ['category'])

    # 3. Create user_professions junction table
    op.create_table('user_professions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('profession_id', sa.Integer(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), default=False),
        sa.Column('notes', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profession_id'], ['professions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'profession_id', name='uq_user_profession')
    )

    # 4. Add access_level to users
    op.add_column('users',
        sa.Column('access_level', sa.String(20), nullable=True, default='staff')
    )
    op.create_index('ix_users_access_level', 'users', ['access_level'])

    # 5. Add label_id to users
    op.add_column('users',
        sa.Column('label_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key('fk_users_label_id', 'users', 'labels', ['label_id'], ['id'])

    # 6. Seed professions data
    professions_table = sa.table('professions',
        sa.column('code', sa.String),
        sa.column('name_fr', sa.String),
        sa.column('name_en', sa.String),
        sa.column('category', sa.String),
        sa.column('sort_order', sa.Integer),
        sa.column('default_access_level', sa.String),
        sa.column('is_active', sa.Boolean)
    )

    professions_data = [
        # MUSICIENS (9)
        {"code": "GUITARISTE", "name_fr": "Guitariste", "name_en": "Guitarist", "category": "musicien", "sort_order": 1, "default_access_level": "staff", "is_active": True},
        {"code": "BATTEUR", "name_fr": "Batteur", "name_en": "Drummer", "category": "musicien", "sort_order": 2, "default_access_level": "staff", "is_active": True},
        {"code": "DIRECTEUR_MUSICAL", "name_fr": "Directeur musical", "name_en": "Musical Director", "category": "musicien", "sort_order": 3, "default_access_level": "staff", "is_active": True},
        {"code": "CLAVIER", "name_fr": "Claviériste", "name_en": "Keyboardist", "category": "musicien", "sort_order": 4, "default_access_level": "staff", "is_active": True},
        {"code": "BASSISTE", "name_fr": "Bassiste", "name_en": "Bassist", "category": "musicien", "sort_order": 5, "default_access_level": "staff", "is_active": True},
        {"code": "PERCUSSIONS", "name_fr": "Percussionniste", "name_en": "Percussionist", "category": "musicien", "sort_order": 6, "default_access_level": "staff", "is_active": True},
        {"code": "CORDES", "name_fr": "Musicien cordes", "name_en": "String Musician", "category": "musicien", "sort_order": 7, "default_access_level": "staff", "is_active": True},
        {"code": "CHORISTE", "name_fr": "Choriste", "name_en": "Backing Vocalist", "category": "musicien", "sort_order": 8, "default_access_level": "staff", "is_active": True},
        {"code": "DJ", "name_fr": "DJ", "name_en": "DJ", "category": "musicien", "sort_order": 9, "default_access_level": "staff", "is_active": True},
        # ARTISTES (2)
        {"code": "ARTISTE_PRINCIPAL", "name_fr": "Artiste principal", "name_en": "Main Artist", "category": "artiste", "sort_order": 1, "default_access_level": "staff", "is_active": True},
        {"code": "PREMIERE_PARTIE", "name_fr": "Première partie", "name_en": "Opening Act", "category": "artiste", "sort_order": 2, "default_access_level": "staff", "is_active": True},
        # TECHNICIENS (13)
        {"code": "INGE_SON_FACADE", "name_fr": "Ingénieur son façade", "name_en": "FOH Sound Engineer", "category": "technicien", "sort_order": 1, "default_access_level": "staff", "is_active": True},
        {"code": "INGE_SON_RETOUR", "name_fr": "Ingénieur son retour", "name_en": "Monitor Engineer", "category": "technicien", "sort_order": 2, "default_access_level": "staff", "is_active": True},
        {"code": "CHEF_LUMIERE", "name_fr": "Chef éclairagiste", "name_en": "Lighting Director", "category": "technicien", "sort_order": 3, "default_access_level": "staff", "is_active": True},
        {"code": "ASSISTANT_LUMIERE", "name_fr": "Assistant lumière", "name_en": "Lighting Assistant", "category": "technicien", "sort_order": 4, "default_access_level": "staff", "is_active": True},
        {"code": "CHEF_PLATEAU", "name_fr": "Chef plateau", "name_en": "Stage Manager", "category": "technicien", "sort_order": 5, "default_access_level": "staff", "is_active": True},
        {"code": "TECHNICIEN_PLATEAU", "name_fr": "Technicien plateau", "name_en": "Stage Technician", "category": "technicien", "sort_order": 6, "default_access_level": "staff", "is_active": True},
        {"code": "ROAD", "name_fr": "Road", "name_en": "Roadie", "category": "technicien", "sort_order": 7, "default_access_level": "staff", "is_active": True},
        {"code": "BACKLINE", "name_fr": "Backline", "name_en": "Backline Tech", "category": "technicien", "sort_order": 8, "default_access_level": "staff", "is_active": True},
        {"code": "REGISSEUR_PLATEAU", "name_fr": "Régisseur plateau", "name_en": "Stage Director", "category": "technicien", "sort_order": 9, "default_access_level": "staff", "is_active": True},
        {"code": "REGISSEUR_SON", "name_fr": "Régisseur son", "name_en": "Sound Director", "category": "technicien", "sort_order": 10, "default_access_level": "staff", "is_active": True},
        {"code": "REGISSEUR_LUMIERE", "name_fr": "Régisseur lumière", "name_en": "Lighting Supervisor", "category": "technicien", "sort_order": 11, "default_access_level": "staff", "is_active": True},
        {"code": "REGISSEUR_GENERAL", "name_fr": "Régisseur général", "name_en": "Production Manager", "category": "technicien", "sort_order": 12, "default_access_level": "manager", "is_active": True},
        {"code": "TECH_VIDEO", "name_fr": "Technicien vidéo", "name_en": "Video Technician", "category": "technicien", "sort_order": 13, "default_access_level": "staff", "is_active": True},
        # PRODUCTION (4)
        {"code": "TOUR_MANAGER", "name_fr": "Tour manager", "name_en": "Tour Manager", "category": "production", "sort_order": 1, "default_access_level": "manager", "is_active": True},
        {"code": "CHARGE_PRODUCTION", "name_fr": "Chargé de production", "name_en": "Production Coordinator", "category": "production", "sort_order": 2, "default_access_level": "staff", "is_active": True},
        {"code": "CHARGE_COMMUNICATION", "name_fr": "Chargé de communication", "name_en": "PR Coordinator", "category": "production", "sort_order": 3, "default_access_level": "staff", "is_active": True},
        {"code": "BOOKER", "name_fr": "Booker", "name_en": "Booking Agent", "category": "production", "sort_order": 4, "default_access_level": "staff", "is_active": True},
        # STYLE (3)
        {"code": "MAQUILLEUR", "name_fr": "Maquilleur/Maquilleuse", "name_en": "Makeup Artist", "category": "style", "sort_order": 1, "default_access_level": "staff", "is_active": True},
        {"code": "HABILLEUR", "name_fr": "Habilleur/Habilleuse", "name_en": "Wardrobe Assistant", "category": "style", "sort_order": 2, "default_access_level": "staff", "is_active": True},
        {"code": "CHEF_COSTUME", "name_fr": "Chef costume", "name_en": "Costume Designer", "category": "style", "sort_order": 3, "default_access_level": "staff", "is_active": True},
        # SECURITE (2)
        {"code": "CHEF_SECURITE", "name_fr": "Chef sécurité", "name_en": "Security Director", "category": "securite", "sort_order": 1, "default_access_level": "staff", "is_active": True},
        {"code": "AGENT_SECURITE", "name_fr": "Agent sécurité", "name_en": "Security Guard", "category": "securite", "sort_order": 2, "default_access_level": "viewer", "is_active": True},
        # MANAGEMENT (2)
        {"code": "MANAGER_ARTISTE", "name_fr": "Manager", "name_en": "Artist Manager", "category": "management", "sort_order": 1, "default_access_level": "manager", "is_active": True},
        {"code": "COMMUNITY_MANAGER", "name_fr": "Community manager", "name_en": "Community Manager", "category": "management", "sort_order": 2, "default_access_level": "staff", "is_active": True},
    ]

    op.bulk_insert(professions_table, professions_data)

    # 7. Migrate existing users to default access level based on their roles
    connection = op.get_bind()

    # Set default access_level for all users
    connection.execute(sa.text(
        "UPDATE users SET access_level = 'staff' WHERE access_level IS NULL"
    ))

    # Upgrade MANAGER role users to 'manager' access level
    connection.execute(sa.text("""
        UPDATE users SET access_level = 'manager'
        WHERE id IN (
            SELECT ur.user_id FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE r.name IN ('MANAGER', 'MANAGEMENT', 'AGENT')
        )
    """))

    # Set PROMOTER and VENUE_CONTACT to 'external'
    connection.execute(sa.text("""
        UPDATE users SET access_level = 'external'
        WHERE id IN (
            SELECT ur.user_id FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE r.name IN ('PROMOTER', 'VENUE_CONTACT')
        )
        AND access_level = 'staff'
    """))

    # Set CALENDAR_VIEWER and LABEL to 'viewer'
    connection.execute(sa.text("""
        UPDATE users SET access_level = 'viewer'
        WHERE id IN (
            SELECT ur.user_id FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE r.name IN ('CALENDAR_VIEWER', 'LABEL')
        )
        AND access_level = 'staff'
    """))


def downgrade():
    # Remove foreign key first
    op.drop_constraint('fk_users_label_id', 'users', type_='foreignkey')

    # Drop columns from users
    op.drop_index('ix_users_access_level', 'users')
    op.drop_column('users', 'label_id')
    op.drop_column('users', 'access_level')

    # Drop tables
    op.drop_table('user_professions')
    op.drop_index('ix_professions_category', 'professions')
    op.drop_index('ix_professions_code', 'professions')
    op.drop_table('professions')
    op.drop_index('ix_labels_code', 'labels')
    op.drop_table('labels')
