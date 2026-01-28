# Patterns Appris - Tour Manager

## 2026-01-12: Quick Start avec SQLite

**Contexte**: Demarrage rapide sans PostgreSQL

**Pattern**:
1. Modifier `.env`: `DATABASE_URL=sqlite:///tour_manager_dev.db`
2. Activer venv: `source venv/Scripts/activate`
3. Installer deps: `pip install -r requirements.txt`
4. Creer tables directement (evite conflits migrations Alembic):
   ```python
   from app import create_app, db
   app = create_app('development')
   with app.app_context():
       db.create_all()
   ```
5. Init roles: `flask init-db`
6. Seed data demo: `python seed_data.py`
7. Lancer: `flask run --host=0.0.0.0 --port=5001`

**Comptes demo**:
- manager@tourmanager.com / Manager123! (MANAGER - acces complet)
- lead@cosmictravelers.com / Lead123! (MUSICIAN)

**Note**: Utiliser `db.create_all()` au lieu de `flask db upgrade` evite les erreurs de migration "duplicate column" avec SQLite.

## 2026-01-12: Debug Login Flask

**Contexte**: Login echoue sans message clair

**Pattern**: Ajouter debug logging dans routes.py pour diagnostiquer:
```python
if request.method == 'POST':
    current_app.logger.warning(f'[DEBUG] POST received - email: {form.email.data}')
    current_app.logger.warning(f'[DEBUG] Form validates: {form.validate()}')
    current_app.logger.warning(f'[DEBUG] Form errors: {form.errors}')
```

**Note**: Les POST /auth/login retournant 200 au lieu de 302 indiquent un echec de validation de formulaire (CSRF, validation fields, ou credentials incorrects).
