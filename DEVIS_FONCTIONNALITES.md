# TOUR MANAGER - Studio Palenque
## Document de Specification des Fonctionnalites

**Version:** 1.0
**Date:** Janvier 2026
**Editeur:** Studio Palenque

---

## RESUME EXECUTIF

**Tour Manager** est une application web professionnelle de gestion de tournees musicales, developpee sur mesure pour repondre aux besoins specifiques de l'industrie du spectacle vivant.

| Metrique | Valeur |
|----------|--------|
| Modules fonctionnels | 12 |
| Endpoints/Routes | 150+ |
| Modeles de donnees | 15 |
| Types de logistique | 17 |
| Formats d'export | PDF, CSV, iCal |

---

## 1. AUTHENTIFICATION & GESTION DES UTILISATEURS

### Fonctionnalites
- Connexion securisee avec email/mot de passe
- Inscription avec workflow d'approbation administrateur
- Reinitialisation de mot de passe par token securise
- Systeme d'invitation pour nouveaux membres
- Verrouillage de compte apres tentatives echouees
- Controle d'acces base sur les roles (RBAC)

### Donnees utilisateur
- Informations personnelles
- Preferences de voyage (compagnie aerienne, siege, repas)
- Contact d'urgence
- Restrictions alimentaires et allergies
- Preferences de notifications

**Complexite:** Moyenne | **Estimation:** 5-7 jours

---

## 2. GESTION DES GROUPES/ARTISTES

### Fonctionnalites
- Creation et edition de profils de groupes
- Gestion des logos (upload local ou URL externe)
- Ajout/suppression de membres avec roles
- Attribution d'instruments et fonctions
- Systeme de manager unique par groupe
- Liens vers reseaux sociaux et site web

### Donnees
- Nom, genre musical, biographie
- Logo, site web, liens sociaux
- Liste des membres avec roles

**Complexite:** Moyenne | **Estimation:** 4-5 jours

---

## 3. GESTION DES TOURNEES

### Fonctionnalites
- Creation de tournees avec dates de debut/fin
- Workflow de statut: BROUILLON → ACTIF → TERMINE → ARCHIVE
- Duplication complete d'une tournee existante
- Vue calendrier interactive (FullCalendar)
- Vue carte interactive (Leaflet.js)
- Export iCal pour synchronisation calendrier externe
- Vue d'ensemble avec statistiques

### Types d'evenements supportes
1. Concert (Show)
2. Jour de repos (Day Off)
3. Voyage (Travel)
4. Studio
5. Promo
6. Repetition (Rehearsal)
7. Presse
8. Meet & Greet
9. Photo/Video
10. Autre

**Complexite:** Haute | **Estimation:** 8-10 jours

---

## 4. GESTION DES DATES/STOPS

### Fonctionnalites
- Ajout de dates avec lieu et horaires
- 10 creneaux horaires configurables:
  - Load-in
  - Appel equipe (Crew Call)
  - Appel artistes
  - Catering
  - Soundcheck
  - Presse
  - Meet & Greet
  - Ouverture portes
  - SET TIME
  - Couvre-feu
- Workflow de statut: BROUILLON → EN ATTENTE → CONFIRME → JOUE → REGLE
- Assignment de membres specifiques par date
- Suivi financier par date

### Donnees financieres par date
- Montant du cachet garanti
- Pourcentage door deal
- Prix du billet et URL billetterie
- Frais de billetterie (configurable 2-10%)
- Devise

**Complexite:** Haute | **Estimation:** 7-8 jours

---

## 5. GESTION DES SALLES/VENUES

### Fonctionnalites
- Creation de fiches salles completes
- Geocodage automatique des adresses (Nominatim API)
- Generation automatique liens Google Maps
- Gestion des contacts par salle
- Types de salles: Club, Theatre, Arena, Festival

### Donnees techniques
- Nom, adresse complete, GPS
- Capacite, type de salle
- Specifications techniques, dimensions scene
- Informations load-in, parking
- Backline disponible
- Contacts multiples avec roles

**Complexite:** Moyenne | **Estimation:** 5-6 jours

---

## 6. GESTION DES GUESTLISTS

### Fonctionnalites
- Ajout d'invites avec accompagnants (plus-ones)
- Workflow d'approbation: EN ATTENTE → APPROUVE → ENTRE
- Interface de check-in rapide pour la salle
- Operations en masse (approbation/refus multiple)
- Export CSV des listes
- Recherche AJAX en temps reel
- Statistiques de frequentation

### Types d'entrees
1. Invite (Guest)
2. Artiste
3. Industrie
4. Presse
5. VIP
6. Invitation (Comp)
7. Accreditation travail (Working)

**Complexite:** Haute | **Estimation:** 8-10 jours

---

## 7. GESTION LOGISTIQUE

### Fonctionnalites
- 17 types de logistique supportes
- Workflow de statut: EN ATTENTE → RESERVE → CONFIRME → TERMINE
- Assignation nominative (sieges avion, chambres hotel)
- Geocodage automatique des lieux
- Contacts locaux par element
- Vue mobile optimisee pour tournee
- Export iCal de l'itineraire
- Vue timeline chronologique

### Types de logistique
| Transport | Hebergement | Autre |
|-----------|-------------|-------|
| Vol | Hotel | Equipement |
| Train | Appartement | Backline |
| Bus | | Catering |
| Ferry | | Repas |
| Location voiture | | Parking |
| Taxi | | Visa |
| Navette | | Assurance |

### Day Sheet
- Resume quotidien complet
- Export PDF professionnel
- Version mobile optimisee
- Tous horaires et contacts

**Complexite:** Haute | **Estimation:** 10-12 jours

---

## 8. GESTION DOCUMENTAIRE

### Fonctionnalites
- Upload de fichiers (max 16 Mo)
- Types supportes: PDF, JPG, PNG, GIF, DOC, DOCX, XLS, XLSX
- Suivi des dates d'expiration
- Alertes documents expirant (90 jours)
- Visualisation inline (PDF, images)
- Association a utilisateur, groupe ou tournee
- Controle d'acces par proprietaire

### Types de documents
1. Rider
2. Passeport
3. Visa
4. Contrat
5. Assurance
6. Permis de travail
7. Autre

**Complexite:** Moyenne | **Estimation:** 5-6 jours

---

## 9. RAPPORTS & SETTLEMENTS FINANCIERS

### Fonctionnalites
- Dashboard avec KPIs
- Calculs automatiques:
  - **GBOR** (Gross Box Office Revenue)
  - **NBOR** (Net Box Office Revenue)
  - Split Point dynamique
  - Door Deal
- Suivi des depenses promoteur
- Generation PDF settlements professionnels
- Export CSV pour analyse
- Graphiques et visualisations

### Contenu Settlement PDF
- Informations groupe et salle
- Detail billetterie (capacite, vendus, taux remplissage)
- Calcul GBOR → NBOR (apres frais billetterie)
- Depenses promoteur detaillees
- Calcul paiement artiste
- Zone de signatures

**Complexite:** Haute | **Estimation:** 6-8 jours

---

## 10. SYSTEME DE NOTIFICATIONS

### Fonctionnalites
- Notifications in-app temps reel
- Compteur non-lus avec dropdown
- Types: Info, Succes, Avertissement, Erreur
- Categories: Tournee, Guestlist, Systeme, Groupe
- Marquage lu/non-lu
- Suppression individuelle ou en masse
- API JSON pour integration

**Complexite:** Moyenne | **Estimation:** 3-4 jours

---

## 11. PARAMETRES & ADMINISTRATION

### Fonctionnalites utilisateur
- Edition profil et preferences voyage
- Changement de mot de passe
- Preferences de notifications
- Upload documents personnels

### Fonctionnalites administrateur
- Liste et gestion des utilisateurs
- Approbation des inscriptions
- Creation/invitation d'utilisateurs
- Suppression soft et hard
- Renvoi d'invitations

### Integrations
- Google Calendar (OAuth)
- Microsoft Outlook (OAuth)

**Complexite:** Moyenne | **Estimation:** 5-6 jours

---

## 12. DASHBOARD & RECHERCHE GLOBALE

### Fonctionnalites
- Tableau de bord personnalise
- Statistiques en temps reel
- Calendrier global multi-tournees
- Recherche unifiee (tournees, dates, salles, groupes)
- Evenements autonomes (hors tournee)
- Endpoint health check pour monitoring

**Complexite:** Moyenne | **Estimation:** 4-5 jours

---

## 13. COMPOSANTS TECHNIQUES AVANCES

### A. Geocodage Automatique
- Integration API Nominatim (OpenStreetMap)
- Geocodage automatique des adresses
- Coordonnees GPS stockees en base

### B. Cartes Interactives (Leaflet.js)
- Affichage multi-couches (rue, satellite)
- Marqueurs pour salles, hotels, transports
- Calcul de distances entre points
- Responsive mobile

### C. Generation PDF (xhtml2pdf)
- Settlements financiers professionnels
- Day Sheets complets
- Planning de tournee
- Compatible cloud (pas de dependances systeme)

### D. Export Calendrier (iCal)
- Format .ics standard
- Compatible Google Calendar, Outlook, Apple
- Tournees et logistique exportables

### E. Interface Responsive
- Framework Bootstrap 5
- Vues mobiles optimisees
- Compatible tablettes et smartphones

### F. Securite
- Tokens securises pour reinitialisation
- Protection CSRF
- Controle d'acces granulaire (RBAC)
- Validation des fichiers uploades

**Complexite:** Haute | **Estimation:** 15-20 jours (reparti)

---

## 14. INTERFACE UTILISATEUR

### Templates developpes
| Section | Nombre de vues |
|---------|----------------|
| Authentification | 8 |
| Groupes | 5 |
| Tournees | 12 |
| Salles | 5 |
| Guestlist | 8 |
| Logistique | 10 |
| Documents | 6 |
| Rapports | 5 |
| Parametres | 8 |
| Notifications | 3 |
| Dashboard | 4 |
| Composants reutilisables | 10+ |
| Emails | 5+ |

**Total:** 90+ templates HTML

**Complexite:** Haute | **Estimation:** 8-10 jours

---

## 15. BASE DE DONNEES

### Modeles principaux
| Modele | Description |
|--------|-------------|
| User | Utilisateurs et preferences |
| Band | Groupes/Artistes |
| BandMembership | Membres de groupes |
| Tour | Tournees |
| TourStop | Dates/Concerts |
| Venue | Salles |
| VenueContact | Contacts salles |
| GuestlistEntry | Invites |
| LogisticsInfo | Elements logistique |
| LocalContact | Contacts locaux |
| LogisticsAssignment | Assignations |
| PromotorExpenses | Depenses promoteur |
| Document | Fichiers/Documents |
| Notification | Notifications |
| OAuthToken | Tokens OAuth |

**Total:** 15 tables avec relations

**Complexite:** Moyenne | **Estimation:** 4-5 jours

---

## RECAPITULATIF ESTIMATION

| Module | Jours |
|--------|-------|
| Authentification & Utilisateurs | 6 |
| Gestion Groupes | 5 |
| Gestion Tournees | 9 |
| Gestion Dates/Stops | 8 |
| Gestion Salles | 6 |
| Gestion Guestlists | 9 |
| Gestion Logistique | 11 |
| Gestion Documents | 6 |
| Rapports & Settlements | 7 |
| Notifications | 4 |
| Parametres & Admin | 6 |
| Dashboard & Recherche | 5 |
| Composants techniques | 18 |
| Interface UI | 9 |
| Base de donnees | 5 |
| Tests & Integration | 12 |
| **TOTAL** | **126 jours** |

---

## VALORISATION

### Methode de calcul
- **Jours de developpement estimes:** 126 jours
- **TJM marche 2025/2026:** 485 EUR - 700 EUR

### Estimation tarifaire

| Positionnement | Calcul | Prix HT |
|----------------|--------|---------|
| Prix plancher | 126 j x 400 EUR | 50 400 EUR |
| Prix marche | 126 j x 530 EUR | 66 780 EUR |
| Prix premium | 126 j x 700 EUR | 88 200 EUR |

### Recommandation

**Fourchette recommandee: 55 000 EUR - 70 000 EUR HT**

Ce tarif inclut:
- Developpement complet de l'application
- Interface utilisateur responsive
- Documentation technique
- Support de livraison

Options additionnelles:
- Maintenance annuelle: 10 000 - 12 000 EUR HT/an
- Formation utilisateurs: 2 000 - 3 000 EUR HT
- Hebergement cloud: sur devis

---

## STACK TECHNIQUE

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.11, Flask 3.0 |
| Base de donnees | PostgreSQL 16 |
| Frontend | Bootstrap 5, JavaScript ES6+ |
| Cartes | Leaflet.js, OpenStreetMap |
| Calendrier | FullCalendar 6 |
| PDF | xhtml2pdf |
| Geocodage | Nominatim API |
| Authentification | Flask-Login, OAuth 2.0 |

---

## LIVRABLES

1. Code source complet de l'application
2. Base de donnees PostgreSQL avec migrations
3. Documentation technique
4. Guide d'installation et deploiement
5. Acces au repository Git

---

*Document genere le 9 janvier 2026*
*Studio Palenque - Tour Manager v1.0*
