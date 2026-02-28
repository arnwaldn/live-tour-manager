# Guide de Déploiement - GigRoute

Ce guide couvre le déploiement de GigRoute en production avec support complet des intégrations OAuth.

---

## Table des matières

1. [Prérequis](#prérequis)
2. [Option 1 : Railway (Recommandé)](#option-1--railway-recommandé)
3. [Option 2 : Render](#option-2--render)
4. [Option 3 : VPS (DigitalOcean/Hetzner)](#option-3--vps)
5. [Configuration Post-Déploiement](#configuration-post-déploiement)
6. [Checklist Production](#checklist-production)

---

## Prérequis

Avant de déployer, assurez-vous d'avoir :

- [ ] Code source prêt (Git repository)
- [ ] Un domaine personnalisé (optionnel mais recommandé)
- [ ] Credentials OAuth préparés (voir `docs/OAUTH_SETUP.md`)

---

## Option 1 : Railway (Recommandé)

**Pourquoi Railway ?**
- Déploiement en 5 minutes
- SSL automatique (HTTPS)
- PostgreSQL inclus
- Variables d'environnement faciles à gérer
- Prix : ~$5-20/mois selon usage

### Étape 1 : Créer un compte Railway

1. Allez sur [railway.app](https://railway.app)
2. Connectez-vous avec GitHub

### Étape 2 : Nouveau projet

1. Cliquez **New Project**
2. Choisissez **Deploy from GitHub repo**
3. Sélectionnez votre repo GigRoute
4. Railway détecte automatiquement que c'est une app Python/Flask

### Étape 3 : Ajouter PostgreSQL

1. Dans votre projet, cliquez **+ New**
2. Choisissez **Database** → **PostgreSQL**
3. Railway lie automatiquement la variable `DATABASE_URL`

### Étape 4 : Variables d'environnement

1. Cliquez sur votre service (pas la database)
2. Allez dans l'onglet **Variables**
3. Ajoutez toutes les variables de `.env.example` :

```
FLASK_ENV=production
SECRET_KEY=<générer avec: python -c "import secrets; print(secrets.token_hex(32))">

# OAuth (voir docs/OAUTH_SETUP.md)
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=https://votre-app.up.railway.app/integrations/google/callback

MICROSOFT_CLIENT_ID=xxx
MICROSOFT_CLIENT_SECRET=xxx
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=https://votre-app.up.railway.app/integrations/outlook/callback

# Email (optionnel)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=xxx
MAIL_PASSWORD=xxx
```

### Étape 5 : Domaine personnalisé (optionnel)

1. Dans **Settings** → **Domains**
2. Cliquez **Generate Domain** pour un sous-domaine Railway gratuit
   OU
3. Cliquez **Add Custom Domain** pour votre propre domaine

### Étape 6 : Déployer

Railway déploie automatiquement à chaque push sur la branche main.

**URL finale** : `https://votre-app.up.railway.app` ou votre domaine custom.

---

## Option 2 : Render

**Pourquoi Render ?**
- Free tier généreux (avec limitations)
- SSL automatique
- Déploiement simple depuis GitHub
- Prix : Gratuit (limité) à $7/mois

### Étape 1 : Créer un compte Render

1. Allez sur [render.com](https://render.com)
2. Connectez-vous avec GitHub

### Étape 2 : Nouveau Web Service

1. Cliquez **New** → **Web Service**
2. Connectez votre repo GitHub
3. Configurez :
   - **Name** : gigroute
   - **Region** : Frankfurt (EU) ou proche de vos users
   - **Branch** : main
   - **Runtime** : Python 3
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `gunicorn -w 4 -b 0.0.0.0:$PORT "app:create_app()"`

### Étape 3 : Ajouter PostgreSQL

1. Cliquez **New** → **PostgreSQL**
2. Choisissez le plan (Free ou Starter)
3. Copiez l'**Internal Database URL**
4. Ajoutez-la comme variable `DATABASE_URL` dans votre web service

### Étape 4 : Variables d'environnement

Dans votre Web Service → **Environment** :

```
FLASK_ENV=production
SECRET_KEY=<générer un secret>
DATABASE_URL=<copié de PostgreSQL>
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=https://gigroute.onrender.com/integrations/google/callback
MICROSOFT_CLIENT_ID=xxx
MICROSOFT_CLIENT_SECRET=xxx
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=https://gigroute.onrender.com/integrations/outlook/callback
```

### Étape 5 : Déployer

Cliquez **Create Web Service**. Render déploie automatiquement.

**URL finale** : `https://gigroute.onrender.com`

> **Note Free Tier** : Le service s'éteint après 15 min d'inactivité et met ~30s à redémarrer.

---

## Option 3 : VPS

**Pourquoi un VPS ?**
- Contrôle total
- Prix fixe prévisible
- Pas de limitations de "free tier"
- Prix : ~$5-12/mois

### Fournisseurs recommandés

| Fournisseur | Prix min | Datacenter EU | Note |
|-------------|----------|---------------|------|
| Hetzner | 4€/mois | ✅ Allemagne | Meilleur rapport qualité/prix |
| DigitalOcean | $6/mois | ✅ Amsterdam | Très populaire, bonne doc |
| OVH | 3.50€/mois | ✅ France | Français, bon support |
| Vultr | $5/mois | ✅ Amsterdam | Simple et efficace |

### Étape 1 : Créer un VPS

1. Choisissez Ubuntu 22.04 LTS
2. Taille minimale : 1 vCPU, 1GB RAM, 25GB SSD
3. Notez l'IP publique

### Étape 2 : Configuration initiale

```bash
# Connexion SSH
ssh root@VOTRE_IP

# Mise à jour système
apt update && apt upgrade -y

# Installer les dépendances
apt install -y python3 python3-pip python3-venv postgresql nginx certbot python3-certbot-nginx git

# Créer utilisateur app
adduser gigroute
usermod -aG sudo gigroute
```

### Étape 3 : Configurer PostgreSQL

```bash
sudo -u postgres psql

CREATE USER gigroute WITH PASSWORD 'motdepasse_securise';
CREATE DATABASE gigroute OWNER gigroute;
\q
```

### Étape 4 : Déployer l'application

```bash
# En tant que gigroute
su - gigroute
cd ~

# Cloner le repo
git clone https://github.com/votre-user/gigroute.git
cd gigroute

# Environnement virtuel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configuration
cp .env.example .env
nano .env  # Éditer avec vos valeurs
```

### Étape 5 : Configurer Gunicorn (service systemd)

Créer `/etc/systemd/system/gigroute.service` :

```ini
[Unit]
Description=GigRoute Flask App
After=network.target

[Service]
User=gigroute
WorkingDirectory=/home/gigroute/gigroute
Environment="PATH=/home/gigroute/gigroute/venv/bin"
EnvironmentFile=/home/gigroute/gigroute/.env
ExecStart=/home/gigroute/gigroute/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable gigroute
sudo systemctl start gigroute
```

### Étape 6 : Configurer Nginx

Créer `/etc/nginx/sites-available/gigroute` :

```nginx
server {
    listen 80;
    server_name votredomaine.com www.votredomaine.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/gigroute/gigroute/app/static;
        expires 30d;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/gigroute /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Étape 7 : SSL avec Let's Encrypt

```bash
sudo certbot --nginx -d votredomaine.com -d www.votredomaine.com
```

Certbot configure automatiquement HTTPS et le renouvellement auto.

---

## Configuration Post-Déploiement

### 1. Mettre à jour les URIs OAuth

Une fois votre domaine final connu, mettez à jour :

**Google Cloud Console :**
- APIs & Services → Credentials → Votre OAuth Client
- Ajoutez l'URI de production : `https://votredomaine.com/integrations/google/callback`

**Azure Portal :**
- App registrations → GigRoute → Authentication
- Ajoutez l'URI : `https://votredomaine.com/integrations/outlook/callback`

### 2. Initialiser la base de données

```bash
# SSH sur votre serveur ou via Railway CLI
flask db upgrade
flask init-db
```

### 3. Créer le premier utilisateur admin

```bash
flask shell
```

```python
from app.models.user import User, Role
from app.extensions import db

# Créer un admin
admin = User(
    email='admin@votredomaine.com',
    first_name='Admin',
    last_name='GigRoute',
    is_active=True
)
admin.set_password('motdepasse_temporaire')

# Assigner le rôle Manager
manager_role = Role.query.filter_by(name='MANAGER').first()
if manager_role:
    admin.roles.append(manager_role)

db.session.add(admin)
db.session.commit()
```

---

## Checklist Production

### Sécurité
- [ ] `SECRET_KEY` généré de manière sécurisée (32+ caractères aléatoires)
- [ ] `FLASK_ENV=production`
- [ ] HTTPS activé (SSL)
- [ ] Mots de passe base de données forts
- [ ] Secrets OAuth non exposés dans le code

### Performance
- [ ] Gunicorn avec multiple workers (`-w 4` minimum)
- [ ] Assets statiques servis par Nginx (si VPS)
- [ ] Base de données sur SSD

### Monitoring
- [ ] Logs configurés (`logs/gigroute.log`)
- [ ] Alertes email configurées (optionnel)
- [ ] Backups base de données automatiques

### OAuth
- [ ] URIs de callback mises à jour avec domaine production
- [ ] Test de connexion Google réussi
- [ ] Test de connexion Outlook réussi

---

## Maintenance

### Mise à jour de l'application

**Railway/Render :** Push sur main → déploiement automatique

**VPS :**
```bash
cd /home/gigroute/gigroute
git pull
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade
sudo systemctl restart gigroute
```

### Backups base de données

```bash
# Backup manuel
pg_dump gigroute > backup_$(date +%Y%m%d).sql

# Restauration
psql gigroute < backup_20240115.sql
```

---

## Support

En cas de problème :

1. Vérifiez les logs : `sudo journalctl -u gigroute -f`
2. Testez la connexion DB : `flask shell` puis `db.session.execute(text('SELECT 1'))`
3. Consultez `docs/OAUTH_SETUP.md` pour les erreurs OAuth
