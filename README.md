# GigRoute

Application web professionnelle de gestion de tournée pour groupes/artistes. Gérez vos tournées, concerts, guestlists et logistique depuis une interface moderne et responsive.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)

## Fonctionnalités

### Gestion des Tournées
- Création et suivi de tournées multi-dates
- Calendrier interactif des concerts
- Statuts de tournée (Planning, Confirmée, Active, Terminée, Annulée)

### Gestion des Concerts (Tour Stops)
- Informations détaillées par date (horaires, venue, statut)
- Soundcheck, ouverture des portes, heure de set
- Liaisons avec venues et logistique

### Guestlists
- Demandes de guestlist avec workflow d'approbation
- Types d'entrée : VIP, Guest, Industrie, Presse, Famille, Staff
- Interface de check-in mobile-optimisée
- Export CSV des guestlists

### Logistique
- Gestion des hôtels, vols, transports terrestres
- Numéros de confirmation et coûts
- Contacts locaux par date

### Système de Rôles (RBAC)
| Rôle | Permissions |
|------|-------------|
| **Manager** | Accès complet (band, tournées, guestlists, logistique) |
| **Musician** | Vue tournée, demandes guestlist |
| **Tech** | Vue show uniquement |
| **Promoter** | Check-in guestlist |
| **Venue Contact** | Check-in guestlist |
| **Guestlist Manager** | Gestion guestlist, check-in, export |

## Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.12, Flask 3.0, SQLAlchemy 2.0 |
| Database | PostgreSQL 16 |
| Frontend | Bootstrap 5.3, Jinja2, JavaScript |
| Auth | Flask-Login, Werkzeug (password hashing) |
| Forms | Flask-WTF, WTForms |
| Sécurité | Flask-Limiter (rate limiting), CSRF protection |
| Production | Gunicorn, Docker, Docker Compose |

## Installation

### Prérequis
- Python 3.12+
- PostgreSQL 16+ (ou Docker)
- pip

### Installation Locale (Développement)

```bash
# 1. Cloner le repo
git clone https://github.com/your-repo/gigroute.git
cd gigroute

# 2. Créer l'environnement virtuel
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
copy .env.example .env
# Éditer .env avec vos valeurs

# 5. Créer la base de données PostgreSQL
# Créer une DB nommée 'gigroute_dev'

# 6. Initialiser la base
flask db upgrade
flask init-db

# 7. (Optionnel) Charger les données de démo
python seed_data.py

# 8. Lancer le serveur
flask run
```

L'application sera accessible sur `http://localhost:5000`

### Déploiement Docker (Production)

```bash
# 1. Cloner le repo
git clone https://github.com/your-repo/gigroute.git
cd gigroute

# 2. Configurer les variables
cp .env.example .env
# IMPORTANT: Modifier SECRET_KEY !

# 3. Build et lancement
docker-compose up -d --build

# 4. Initialiser la base (première fois)
docker-compose exec web flask db upgrade
docker-compose exec web flask init-db
docker-compose exec web python seed_data.py  # optionnel

# 5. Vérifier
curl http://localhost:8000/health
```

L'application sera accessible sur `http://localhost:8000`

## Structure du Projet

```
gigroute/
├── app/
│   ├── __init__.py              # Application factory
│   ├── extensions.py            # Flask extensions
│   ├── config.py                # Configuration
│   │
│   ├── models/                  # SQLAlchemy models
│   │   ├── user.py              # User, Role
│   │   ├── band.py              # Band, BandMembership
│   │   ├── tour.py              # Tour
│   │   ├── venue.py             # Venue, VenueContact
│   │   ├── tour_stop.py         # TourStop (Show)
│   │   ├── guestlist.py         # GuestlistEntry
│   │   └── logistics.py         # LogisticsInfo, LocalContact
│   │
│   ├── blueprints/              # Routes par domaine
│   │   ├── auth/                # Login, register, logout
│   │   ├── main/                # Dashboard, search, health
│   │   ├── bands/               # CRUD Band
│   │   ├── tours/               # CRUD Tour + Calendar
│   │   ├── venues/              # CRUD Venue
│   │   ├── guestlist/           # Guestlist + Check-in
│   │   └── logistics/           # Logistics management
│   │
│   ├── decorators/              # @role_required, etc.
│   ├── templates/               # Jinja2 templates
│   └── static/                  # CSS, JS, images
│
├── tests/                       # pytest tests
├── migrations/                  # Alembic migrations
├── seed_data.py                 # Demo data
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Schéma de Base de Données

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   users     │────<│ user_roles  │>────│    roles    │
└─────────────┘     └─────────────┘     └─────────────┘
       │
       │ manages
       ▼
┌─────────────┐     ┌─────────────┐
│    bands    │────<│   tours     │
└─────────────┘     └─────────────┘
       │                   │
       │ members           │ stops
       ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ memberships │     │ tour_stops  │────>│   venues    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
   ┌───────────┐    ┌───────────┐    ┌───────────┐
   │ guestlist │    │ logistics │    │  contacts │
   │  entries  │    │   info    │    │   local   │
   └───────────┘    └───────────┘    └───────────┘
```

## Comptes de Démo

Après avoir exécuté `python seed_data.py` :

| Email | Mot de passe | Rôle |
|-------|--------------|------|
| manager@gigroute.app | Manager123! | Manager |
| musician1@gigroute.app | Musician123! | Musician |
| musician2@gigroute.app | Musician123! | Musician |
| tech@gigroute.app | Tech123! | Tech |
| promoter@gigroute.app | Promoter123! | Promoter |
| guestlist@gigroute.app | Guestlist123! | Guestlist Manager |

## Tests

```bash
# Exécuter tous les tests
pytest

# Avec couverture
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/test_models.py
pytest tests/test_auth.py
pytest tests/test_routes.py
```

## Variables d'Environnement

| Variable | Description | Exemple |
|----------|-------------|---------|
| `DATABASE_URL` | URL PostgreSQL | `postgresql://user:pass@localhost/gigroute` |
| `SECRET_KEY` | Clé secrète Flask | `your-secret-key-change-in-production` |
| `FLASK_ENV` | Environnement | `development` ou `production` |
| `MAIL_SERVER` | Serveur SMTP | `smtp.gmail.com` |
| `MAIL_PORT` | Port SMTP | `587` |
| `MAIL_USERNAME` | Email SMTP | `your-email@gmail.com` |
| `MAIL_PASSWORD` | Mot de passe SMTP | `your-app-password` |

## API Health Check

```bash
GET /health
```

Réponse :
```json
{
  "status": "healthy",
  "database": "healthy",
  "service": "gigroute"
}
```

## Design Responsive

L'application est optimisée pour tous les appareils :

| Appareil | Breakpoint | Adaptations |
|----------|------------|-------------|
| Mobile | < 768px | Menu hamburger, sidebar offcanvas, cards empilées |
| Tablette | 768px - 992px | Navbar compacte, 2 colonnes |
| Desktop | > 992px | Layout complet, sidebar fixe |

### Interface Check-in Mobile
- Grands boutons tactiles (min 44px)
- Swipe pour actions rapides
- Pull-to-refresh

## Sécurité

- **CSRF Protection** : Tokens sur tous les formulaires
- **Password Hashing** : Werkzeug pbkdf2_sha256
- **Rate Limiting** : Flask-Limiter (5 login/min)
- **XSS Prevention** : Jinja2 auto-escape
- **SQL Injection** : SQLAlchemy parameterized queries
- **Session Security** : Secure cookies, HTTPOnly, SameSite=Lax

## Commandes CLI

```bash
# Initialiser la base (créer rôles par défaut)
flask init-db

# Migrations
flask db migrate -m "Description"
flask db upgrade
flask db downgrade

# Charger données démo
python seed_data.py

# Nettoyer données (ATTENTION: supprime tout)
python seed_data.py --clean
```

## Contribution

1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## Licence

MIT License - voir [LICENSE](LICENSE) pour plus de détails.

---

Développé avec Flask et Bootstrap pour les professionnels de la musique.
