# Tour Manager - Guide de Deploiement

## Table des matieres

1. [Deploiement Railway (Recommande)](#deploiement-railway-recommande)
2. [Deploiement Docker Compose](#deploiement-docker-compose)
3. [Variables d'environnement](#variables-denvironnement)
4. [Modifications continues](#modifications-continues)
5. [Backup et restauration](#backup-et-restauration)
6. [Troubleshooting](#troubleshooting)

---

## Deploiement Railway (Recommande)

Railway offre un deploiement gratuit avec PostgreSQL et Redis inclus.

### Prerequisites

- Compte GitHub avec le repository du projet
- Compte Railway (https://railway.app)

### Etape 1: Preparer le repository

```bash
# S'assurer que tous les fichiers sont commites
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### Etape 2: Creer le projet Railway

1. Aller sur https://railway.app
2. Cliquer "New Project"
3. Selectionner "Deploy from GitHub repo"
4. Autoriser l'acces a votre repository
5. Selectionner `tour-manager`

### Etape 3: Ajouter PostgreSQL

1. Dans le projet Railway, cliquer "New"
2. Selectionner "Database" > "PostgreSQL"
3. La variable `DATABASE_URL` sera automatiquement disponible

### Etape 4: Ajouter Redis

1. Dans le projet Railway, cliquer "New"
2. Selectionner "Database" > "Redis"
3. La variable `REDIS_URL` sera automatiquement disponible

### Etape 5: Configurer les variables d'environnement

Dans Railway Dashboard > Variables, ajouter:

```
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=<generer avec: python scripts/generate_secret.py>
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
RATELIMIT_STORAGE_URL=${{Redis.REDIS_URL}}
CACHE_TYPE=RedisCache
CACHE_REDIS_URL=${{Redis.REDIS_URL}}
GEOAPIFY_API_KEY=<votre cle API>
```

### Etape 6: Deployer

Railway deploie automatiquement apres chaque push sur `main`.

Pour forcer un deploiement manuel:
1. Dashboard Railway > Deployments
2. Cliquer "Redeploy"

### Etape 7: Verifier

```bash
# Verifier le health check
curl https://votre-app.up.railway.app/health

# Reponse attendue:
# {"database":"ok","redis":"ok","status":"healthy","timestamp":"..."}
```

---

## Deploiement Docker Compose

Pour un deploiement sur serveur propre avec Docker.

### Prerequisites

- Docker et Docker Compose installes
- Nom de domaine pointe vers votre serveur
- Ports 80 et 443 ouverts

### Etape 1: Configurer l'environnement

```bash
# Copier le template
cp .env.production.example .env.production

# Editer avec vos valeurs
nano .env.production
```

Variables a modifier:
- `SECRET_KEY`: Generer avec `python scripts/generate_secret.py`
- `DATABASE_URL`: `postgresql://postgres:VOTRE_MOT_DE_PASSE@db:5432/tour_manager`
- `REDIS_URL`: `redis://redis:6379/0`
- `MAIL_*`: Vos identifiants SMTP
- `GEOAPIFY_API_KEY`: Votre cle API

### Etape 2: Configurer Nginx

```bash
# Editer nginx.conf
nano nginx/nginx.conf

# Remplacer VOTRE_DOMAINE par votre domaine reel
# Exemple: ssl_certificate /etc/letsencrypt/live/tourmanager.com/fullchain.pem;
```

### Etape 3: Obtenir les certificats SSL

```bash
# Demarrer le serveur HTTP temporaire
docker-compose up -d nginx

# Obtenir le certificat Let's Encrypt
docker run -it --rm \
  -v $(pwd)/certbot/conf:/etc/letsencrypt \
  -v $(pwd)/certbot/www:/var/www/certbot \
  certbot/certbot certonly \
  --webroot -w /var/www/certbot \
  -d votre-domaine.com \
  --email votre@email.com \
  --agree-tos
```

### Etape 4: Demarrer l'application

```bash
# Mode production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verifier les logs
docker-compose logs -f web
```

### Etape 5: Initialiser la base de donnees

```bash
# Executer les migrations
docker-compose exec web flask db upgrade

# Creer un admin (optionnel)
docker-compose exec web flask create-admin
```

---

## Variables d'environnement

| Variable | Description | Obligatoire |
|----------|-------------|-------------|
| `SECRET_KEY` | Cle secrete Flask (64 caracteres hex) | Oui |
| `DATABASE_URL` | URL PostgreSQL | Oui |
| `REDIS_URL` | URL Redis | Oui |
| `FLASK_ENV` | Environment (`production`) | Oui |
| `FLASK_DEBUG` | Debug mode (`false`) | Oui |
| `GEOAPIFY_API_KEY` | Cle API Geoapify | Non |
| `MAIL_SERVER` | Serveur SMTP | Non |
| `MAIL_PORT` | Port SMTP (587) | Non |
| `MAIL_USERNAME` | Utilisateur SMTP | Non |
| `MAIL_PASSWORD` | Mot de passe SMTP | Non |

### Generer SECRET_KEY

```bash
# Option 1: Script Python
python scripts/generate_secret.py

# Option 2: Commande directe
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Modifications continues

### Avec Railway (recommande)

```bash
# 1. Faire vos modifications localement
# 2. Tester
python -m pytest

# 3. Commiter et pusher
git add .
git commit -m "Description de la modification"
git push origin main

# Railway deploie automatiquement!
```

### Avec Docker Compose

```bash
# 1. Faire vos modifications
# 2. Reconstruire l'image
docker-compose build web

# 3. Redemarrer
docker-compose up -d web

# Zero downtime avec:
docker-compose up -d --no-deps --build web
```

---

## Backup et restauration

### Railway

Railway effectue des backups automatiques de PostgreSQL.

Pour backup manuel:
1. Dashboard > PostgreSQL > Backups
2. Cliquer "Create Backup"

### Docker Compose

```bash
# Backup base de donnees
docker-compose exec db pg_dump -U postgres tour_manager > backup_$(date +%Y%m%d).sql

# Restauration
docker-compose exec -T db psql -U postgres tour_manager < backup_20260128.sql
```

### Backup automatique (cron)

```bash
# Ajouter au crontab
0 2 * * * cd /path/to/tour-manager && docker-compose exec -T db pg_dump -U postgres tour_manager > /backups/tour_manager_$(date +\%Y\%m\%d).sql
```

---

## Troubleshooting

### L'application ne demarre pas

```bash
# Verifier les logs
railway logs  # Sur Railway
docker-compose logs web  # Sur Docker

# Problemes courants:
# - DATABASE_URL non configure
# - SECRET_KEY manquant
# - Port deja utilise
```

### Erreur de connexion base de donnees

```bash
# Verifier que PostgreSQL est accessible
docker-compose exec web python -c "from app import create_app; app = create_app(); print('DB OK')"

# Verifier DATABASE_URL
echo $DATABASE_URL
```

### Erreur Redis

```bash
# Verifier connexion Redis
docker-compose exec web python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"
```

### Health check echoue

```bash
# Tester manuellement
curl -v http://localhost:8000/health

# Verifier que l'app est bien demarree
docker-compose ps
```

### Certificat SSL expire

```bash
# Renouveler le certificat
docker run -it --rm \
  -v $(pwd)/certbot/conf:/etc/letsencrypt \
  -v $(pwd)/certbot/www:/var/www/certbot \
  certbot/certbot renew

# Redemarrer nginx
docker-compose restart nginx
```

---

## Support

- Issues: Ouvrir une issue sur le repository GitHub
- Documentation Flask: https://flask.palletsprojects.com
- Documentation Railway: https://docs.railway.app
- Documentation Docker: https://docs.docker.com

---

*Derniere mise a jour: Janvier 2026*
