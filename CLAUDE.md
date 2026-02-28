# GigRoute (tour-manager)

SaaS de gestion de tournees musicales. Marche cible : musiques actuelles en France.

## Stack

- **Backend**: Flask 3.0, Python 3.12, SQLAlchemy 2.0, Alembic
- **Frontend**: Jinja2 + Bootstrap 5.3, pas de framework JS
- **DB**: PostgreSQL 16 (prod), SQLite in-memory (tests)
- **Auth**: Flask-Login + RBAC 5 niveaux (AccessLevel enum)
- **Payments**: Stripe (Free/Pro SaaS)
- **Deploy**: Docker/Compose + Gunicorn, CI via GitHub Actions

## Architecture

### App Factory Pattern

```
create_app(config_name) → Flask app
  ├── init_extensions()       # extensions.py
  ├── register_blueprints()   # 18 blueprints
  ├── register_error_handlers()
  ├── register_cli_commands()
  ├── register_context_processors()
  ├── register_template_filters()  # French i18n
  └── register_security_headers()  # CSP, HSTS, X-Frame
```

### Blueprints (URL prefixes)

| Blueprint | Prefix | Description |
|-----------|--------|-------------|
| auth | /auth | Login, register, password reset, invite |
| main | / | Dashboard, landing, health |
| bands | /bands | Groupes et membres |
| tours | /tours | Tournees et dates |
| venues | /venues | Salles et contacts |
| guestlist | /guestlist | Listes d'invites et check-in |
| logistics | /logistics | Transport, geocoding, carte |
| reports | /reports | Rapports et analytics |
| settings | /settings | Preferences utilisateur |
| documents | /documents | Documents et PDF |
| notifications | /notifications | Notifications in-app |
| integrations | /integrations | Google Calendar, Microsoft 365 |
| payments | /payments | Paiements crew (cachets, per diem) |
| invoices | /invoices | Factures et export PDF |
| crew | / | Equipe technique, planning |
| advancing | /advancing | Preparation evenements (checklist, rider) |
| billing | /billing | Abonnements SaaS Stripe |
| api | /api/v1 | REST API (JWT, CSRF exempt) |

### Blueprint Structure (convention)

```
app/blueprints/<name>/
  ├── __init__.py     # Blueprint instance: <name>_bp = Blueprint(...)
  ├── routes.py       # Route handlers
  ├── forms.py        # WTForms classes (si formulaires)
  └── templates/      # Optionnel (certains dans app/templates/<name>/)
```

### Models (app/models/)

24 models SQLAlchemy. Cles :
- `User` — AccessLevel enum (ADMIN/MANAGER/STAFF/VIEWER/EXTERNAL), Role M2M
- `Tour` — TourStatus enum, lie a Band
- `TourStop` — Date de concert, lie a Tour + Venue, champs financiers
- `Venue` — Salle avec geocoding
- `GuestlistEntry` — GuestlistStatus + EntryType enums
- `Subscription` — Plans SaaS (Free/Pro), Stripe integration

### Extensions (app/extensions.py)

```python
db = SQLAlchemy()        # ORM
migrate = Migrate()      # Alembic
login_manager            # Flask-Login (vue: auth.login)
csrf = CSRFProtect()     # CSRF (API exempt)
limiter = Limiter()      # Rate limiting (100/min default)
mail = Mail()            # Email
cache = Cache()          # SimpleCache (Redis en prod)
```

## Conventions

### Langue

- **UI** : Francais (flash messages, labels, templates)
- **Code** : Anglais (variables, fonctions, classes, commentaires)
- **Enums** : Anglais (ADMIN, MANAGER, CONFIRMED, PENDING...)

### RBAC

5 niveaux dans `AccessLevel` (str Enum) :
```
ADMIN > MANAGER > STAFF > VIEWER > EXTERNAL
```
Verifier les permissions avec des decorators ou checks dans les routes.

### Tests

- **Framework** : pytest 8.3 + pytest-flask + pytest-cov
- **Config** : `pytest.ini` (coverage min 55%, verbose, short traceback)
- **Fixtures** : `tests/conftest.py` (app, client, session, users, roles, tours...)
- **Pattern** : `tests/test_<module>.py`, classes `Test<Feature>`, methodes `test_<behavior>`
- **Auth helper** : `authenticated_client` fixture (session-based, manager user)
- **Run** : `pytest` (depuis la racine du projet)

### Database

- Dev : `postgresql://postgres:postgres@localhost:5432/tour_manager_dev`
- Test : `sqlite:///:memory:` (pas de DB externe requise)
- Prod : `DATABASE_URL` env var (postgres:// auto-corrige en postgresql://)
- Migrations : Alembic via `flask db migrate` / `flask db upgrade`

### Security

- CSRF sur tous les formulaires (sauf API)
- Rate limiting : 5/min sur login POST, 100/min global
- Session : HttpOnly, SameSite=Lax, Secure en prod
- Lockout : 5 tentatives → verrouillage 15 min
- JWT : cle separee recommandee (JWT_SECRET_KEY)
- Upload : magic bytes validation + secure_filename

## Rebrand en cours

Le projet est en cours de rebrand de "Live Tour Manager" / "Studio Palenque Tour" vers **GigRoute**.

### Identite GigRoute

- **Palette** : Deep Black #0F0F14, Electric Amber #FFB72D, Warm White #FAF8F5
- **Typo** : Outfit (titres), Inter (body), Geist Mono (code)
- **Tagline FR** : "Du bureau au backstage"
- **Assets** : `../gigroute-*.png` (logo, icon, wordmark, social card)

### Plan strategique

Voir `../Plan strategique complet.txt` pour la roadmap complete (4 phases, 20 semaines).

Phase 1 (MVP) — Sprints prioritaires :
1. Bugs critiques + rebrand GigRoute
2. Champs horaires/hebergement/transport par date
3. Permissions RBAC + securite
4. PWA + mobile

## Commandes utiles

```bash
# Dev
flask run                          # Serveur dev
pytest                             # Tests (1096 tests)
pytest --cov=app --cov-report=html # Coverage HTML

# DB
flask db migrate -m "description"  # Nouvelle migration
flask db upgrade                   # Appliquer migrations
flask seed-professions             # Seed metiers

# Docker
docker-compose up                  # Stack complete (nginx+flask+postgres+redis)
```
