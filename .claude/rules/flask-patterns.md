# Flask Patterns — GigRoute

## New Blueprint Checklist

1. Create `app/blueprints/<name>/` with `__init__.py`, `routes.py`, optionally `forms.py`
2. In `__init__.py`: `<name>_bp = Blueprint('<name>', __name__, template_folder='templates')`
3. Import routes at bottom of `__init__.py`: `from app.blueprints.<name> import routes`
4. Register in `app/__init__.py` → `register_blueprints()` with url_prefix
5. Add templates in `app/templates/<name>/` (extends `layouts/base.html`)
6. Add tests in `tests/test_<name>.py`

## Route Pattern

```python
from app.blueprints.<name> import <name>_bp
from flask_login import login_required, current_user
from app.extensions import db, limiter

@<name>_bp.route('/', methods=['GET'])
@login_required
def index():
    # Check permissions via current_user.access_level
    # Query with SQLAlchemy 2.0 style
    # Return render_template('<name>/index.html', ...)
```

## Model Pattern

```python
from app.extensions import db
from enum import Enum

class MyStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"

class MyModel(db.Model):
    __tablename__ = 'my_models'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    # Use db.Enum(MyStatus) for enum columns
    # Use db.relationship() with back_populates (not backref)
```

## Test Pattern

```python
class TestMyFeature:
    def test_requires_auth(self, client):
        resp = client.get('/my-route')
        assert resp.status_code in (302, 401)

    def test_authenticated_access(self, authenticated_client, app):
        resp = authenticated_client.get('/my-route')
        assert resp.status_code == 200

    def test_model_creation(self, app, session):
        obj = MyModel(name='test')
        session.add(obj)
        session.commit()
        assert obj.id is not None
```

## Flash Messages (French)

- Success: `flash('Element cree avec succes.', 'success')`
- Error: `flash('Une erreur est survenue.', 'error')`
- Warning: `flash('Attention : ...', 'warning')`
- Info: `flash('Information : ...', 'info')`

## Form Pattern

```python
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired, Length

class MyForm(FlaskForm):
    name = StringField('Nom', validators=[DataRequired(), Length(max=100)])
```
