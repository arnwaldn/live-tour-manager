# Guide de Configuration OAuth - Tour Manager

Ce guide permet à l'administrateur de configurer les intégrations calendrier **une seule fois**.
Une fois configuré, tous les utilisateurs pourront connecter leurs calendriers en un clic.

---

## Table des matières

1. [Prérequis](#prérequis)
2. [Google Calendar](#google-calendar)
3. [Microsoft Outlook](#microsoft-outlook)
4. [Vérification](#vérification)
5. [Dépannage](#dépannage)

---

## Prérequis

Avant de commencer, assurez-vous d'avoir :

- [ ] Un domaine avec **HTTPS** (SSL obligatoire pour OAuth)
- [ ] Accès admin à votre serveur ou hébergement
- [ ] Un compte Google (pour Google Calendar)
- [ ] Un compte Microsoft (pour Outlook)

> **Note** : Les intégrations OAuth nécessitent HTTPS. En développement local, 
> vous pouvez utiliser `http://localhost:5000` mais en production, HTTPS est obligatoire.

---

## Google Calendar

### Étape 1 : Créer un projet Google Cloud

1. Allez sur [Google Cloud Console](https://console.cloud.google.com)
2. Cliquez sur le sélecteur de projet en haut → **Nouveau projet**
3. Nom du projet : `Tour Manager` (ou le nom de votre choix)
4. Cliquez **Créer**

### Étape 2 : Activer l'API Google Calendar

1. Dans le menu hamburger (☰), allez dans **APIs & Services** → **Bibliothèque**
2. Recherchez `Google Calendar API`
3. Cliquez dessus puis **Activer**

### Étape 3 : Configurer l'écran de consentement OAuth

1. Allez dans **APIs & Services** → **Écran de consentement OAuth**
2. Choisissez **External** (permet à tous les utilisateurs de se connecter)
3. Cliquez **Créer**
4. Remplissez les informations :
   - **Nom de l'application** : Tour Manager
   - **Email d'assistance** : votre email
   - **Logo** : optionnel
   - **Domaines autorisés** : ajoutez votre domaine (ex: `votredomaine.com`)
   - **Coordonnées du développeur** : votre email
5. Cliquez **Enregistrer et continuer**

### Étape 4 : Ajouter les scopes (permissions)

1. Sur l'écran des Scopes, cliquez **Ajouter ou supprimer des champs d'application**
2. Recherchez et ajoutez :
   - `https://www.googleapis.com/auth/calendar` (lecture/écriture calendrier)
   - `https://www.googleapis.com/auth/calendar.events` (événements)
3. Cliquez **Mettre à jour** puis **Enregistrer et continuer**

### Étape 5 : Ajouter des utilisateurs de test (mode test)

1. Ajoutez votre email et ceux des testeurs
2. Cliquez **Enregistrer et continuer**
3. Vérifiez le résumé puis **Retour au tableau de bord**

> **Important** : Tant que l'app n'est pas "vérifiée" par Google, seuls les utilisateurs 
> de test peuvent se connecter. Pour la production, vous devrez soumettre l'app à vérification.

### Étape 6 : Créer les identifiants OAuth2

1. Allez dans **APIs & Services** → **Identifiants**
2. Cliquez **+ Créer des identifiants** → **ID client OAuth**
3. Type d'application : **Application Web**
4. Nom : `Tour Manager Web`
5. **URI de redirection autorisés** : ajoutez exactement :
   ```
   https://VOTRE-DOMAINE/integrations/google/callback
   ```
   (Remplacez `VOTRE-DOMAINE` par votre vrai domaine)
   
   Pour le développement local, ajoutez aussi :
   ```
   http://localhost:5000/integrations/google/callback
   ```
6. Cliquez **Créer**

### Étape 7 : Copier les credentials

Une fenêtre s'affiche avec :
- **ID client** → Copiez dans `GOOGLE_CLIENT_ID`
- **Secret client** → Copiez dans `GOOGLE_CLIENT_SECRET`

Ajoutez dans votre fichier `.env` :
```env
GOOGLE_CLIENT_ID=xxxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=https://VOTRE-DOMAINE/integrations/google/callback
```

---

## Microsoft Outlook

### Étape 1 : Accéder à Azure Portal

1. Allez sur [Azure Portal](https://portal.azure.com)
2. Connectez-vous avec votre compte Microsoft

### Étape 2 : Enregistrer une nouvelle application

1. Recherchez **Azure Active Directory** dans la barre de recherche
2. Dans le menu de gauche, cliquez **App registrations**
3. Cliquez **+ New registration**
4. Remplissez :
   - **Name** : `Tour Manager`
   - **Supported account types** : Choisissez **Accounts in any organizational directory and personal Microsoft accounts**
   - **Redirect URI** :
     - Platform : **Web**
     - URL : `https://VOTRE-DOMAINE/integrations/outlook/callback`
5. Cliquez **Register**

### Étape 3 : Noter l'Application ID

Sur la page de votre app, notez :
- **Application (client) ID** → Copiez dans `MICROSOFT_CLIENT_ID`
- **Directory (tenant) ID** → Utilisez `common` pour supporter tous les comptes

### Étape 4 : Ajouter les permissions API

1. Dans le menu de gauche, cliquez **API permissions**
2. Cliquez **+ Add a permission**
3. Choisissez **Microsoft Graph**
4. Choisissez **Delegated permissions**
5. Recherchez et cochez :
   - `Calendars.ReadWrite` (lecture/écriture calendrier)
   - `User.Read` (info utilisateur basique)
6. Cliquez **Add permissions**

> **Note** : Si vous voyez "Admin consent required", un admin Azure doit approuver.
> Pour les comptes personnels, ce n'est généralement pas nécessaire.

### Étape 5 : Créer un secret client

1. Dans le menu de gauche, cliquez **Certificates & secrets**
2. Dans l'onglet **Client secrets**, cliquez **+ New client secret**
3. Description : `Tour Manager Production`
4. Expiration : Choisissez selon vos besoins (24 mois recommandé)
5. Cliquez **Add**

**IMPORTANT** : Copiez immédiatement la **Value** (pas l'ID) car elle ne sera plus visible après !

### Étape 6 : Copier les credentials

Ajoutez dans votre fichier `.env` :
```env
MICROSOFT_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=https://VOTRE-DOMAINE/integrations/outlook/callback
```

---

## Vérification

### Test de configuration

Après avoir configuré les variables d'environnement :

1. Redémarrez votre application Flask
2. Connectez-vous en tant qu'utilisateur
3. Allez dans **Paramètres** → **Intégrations**
4. Vérifiez que les boutons "Connecter" sont actifs (pas de message "non configuré")

### Test de connexion Google

1. Cliquez **Connecter Google Calendar**
2. Choisissez votre compte Google
3. Acceptez les permissions demandées
4. Vous devriez être redirigé vers Tour Manager avec le message "Connecté avec succès"

### Test de connexion Outlook

1. Cliquez **Connecter Outlook**
2. Choisissez votre compte Microsoft
3. Acceptez les permissions
4. Vous devriez être redirigé avec succès

---

## Dépannage

### Erreur "redirect_uri_mismatch" (Google)

**Cause** : L'URI de redirection ne correspond pas exactement à celle configurée.

**Solution** :
1. Vérifiez que l'URL dans Google Cloud Console correspond **exactement** à `GOOGLE_REDIRECT_URI`
2. Attention aux différences : `http` vs `https`, trailing slash, etc.
3. Après modification, attendez quelques minutes (cache Google)

### Erreur "invalid_client" (Google/Microsoft)

**Cause** : Client ID ou Secret incorrect.

**Solution** :
1. Vérifiez qu'il n'y a pas d'espaces ou caractères invisibles
2. Régénérez un nouveau secret si nécessaire

### Erreur "AADSTS50011" (Microsoft)

**Cause** : URI de redirection non enregistrée.

**Solution** :
1. Dans Azure Portal → App registrations → Votre app → Authentication
2. Ajoutez l'URI exacte utilisée

### Les boutons restent "Non configuré"

**Cause** : Variables d'environnement non chargées.

**Solution** :
1. Vérifiez que le fichier `.env` existe
2. Vérifiez que `python-dotenv` est installé
3. Redémarrez complètement l'application

### Erreur "Access Denied" à la connexion

**Cause** : L'app n'est pas encore vérifiée (Google) ou permissions manquantes (Microsoft).

**Solution Google** :
- En mode test, ajoutez l'utilisateur comme testeur dans l'écran de consentement OAuth
- Pour la production, soumettez l'app à vérification Google

**Solution Microsoft** :
- Vérifiez que les permissions `Calendars.ReadWrite` sont bien ajoutées
- Si "Admin consent required", demandez à un admin Azure d'approuver

---

## Checklist finale

- [ ] Projet Google Cloud créé
- [ ] Google Calendar API activée
- [ ] Écran de consentement OAuth configuré
- [ ] Credentials Google créés et copiés dans `.env`
- [ ] App Azure enregistrée
- [ ] Permissions Microsoft Graph ajoutées
- [ ] Secret client Microsoft créé et copié dans `.env`
- [ ] URIs de redirection correctes des deux côtés
- [ ] Application redémarrée après modification `.env`
- [ ] Test de connexion réussi pour Google
- [ ] Test de connexion réussi pour Outlook

---

## Support

Si vous rencontrez des problèmes :

1. Vérifiez les logs de l'application (`logs/tour_manager.log`)
2. Consultez la section Dépannage ci-dessus
3. Vérifiez la documentation officielle :
   - [Google OAuth2](https://developers.google.com/identity/protocols/oauth2)
   - [Microsoft Identity Platform](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
