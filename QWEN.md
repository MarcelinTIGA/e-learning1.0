# E-Learning Platform — Contexte Projet

## Vue d'ensemble

Backend API Django pour une plateforme e-learning multi-rôles (apprenant, formateur, administrateur). Le projet utilise Django REST Framework avec authentification JWT, django-allauth pour l'auth sociale (Google, Facebook), et dj-rest-auth pour les endpoints d'authentification.

**État actuel** : Le squelette est en place. Le modèle `User` personnalisé et `UserProfile` sont implémentés. Tous les autres apps domain (`courses`, `enrollments`, `progress`, `quizzes`, `certificates`, `dashboard`) existent mais n'ont **pas encore de modèles, vues ou logique métier**. Les URLs de toutes les apps sont vides. Aucune migration locale n'a été créée.

## Stack Technique

| Technologie | Version / Détail |
|---|---|
| Python | 3.13.7 (venv dans `env/`) |
| Django | 6.0.4 |
| Django REST Framework | 3.17.1 |
| SimpleJWT | 5.5.1 (access 30 min, refresh 7 jours, rotation + blacklist) |
| django-cors-headers | 4.7.0 |
| django-filter | 25.1 |
| dj-rest-auth | 7.2.0 |
| django-allauth | 65.15.1 (Google, Facebook) |
| Pillow | 11.2.1 (images/avatars) |
| reportlab | 4.4.0 (génération PDF certificats) |
| python-decouple | 3.8 (gestion .env) |
| DB | SQLite (`db.sqlite3`) |

## Structure du Projet

```
e-learning 1.0/
├── manage.py
├── requirements.txt
├── db.sqlite3
├── env/                          # venv Python 3.13.7
├── elearning_backend/            # Configuration Django principale
│   ├── settings.py
│   ├── urls.py                   # Point d'entrée URL, inclut toutes les apps
│   ├── wsgi.py / asgi.py
│   └── __init__.py
├── apps/                         # Apps modulaires
│   ├── users/                    # ✅ User (custom) + UserProfile
│   ├── authentication/           # 🔲 Login, registration, session
│   ├── courses/                  # 🔲 Cours, modules, contenu
│   ├── enrollments/              # 🔲 Inscriptions étudiants
│   ├── progress/                 🔲 Suivi progression
│   ├── quizzes/                  # 🔲 Questions, notation
│   ├── certificates/             # 🔲 Délivrance certificats PDF
│   └── dashboard/                # 🔲 Analytics, reporting
└── VISION GLOBALE DU PRODUIT EFG.pdf  # Document de vision produit
```

## Modèle Utilisateur (implémenté)

**`apps/users/models.py`** :

- **`User`** — `AbstractBaseUser` + `PermissionsMixin`
  - PK : `UUIDField`
  - `email` (unique, used as USERNAME_FIELD)
  - `first_name`, `last_name`, `role` (Apprenant / Formateur / Administrateur)
  - `is_also_admin` (booléen pour droits admin additionnels)
  - `is_active`, `is_staff`, `date_joined`
- **`UserProfile`** — `OneToOneField` vers User
  - `phone`, `bio`, `avatar` (ImageField), timestamps

## Configuration Clé (`settings.py`)

- **`AUTH_USER_MODEL`** : `'users.User'`
- **`LANGUAGE_CODE`** : `'fr-fr'`
- **JWT** : Access 30 min, Refresh 7 jours, rotation + blacklist activées
- **CORS** : `CORS_ALLOW_ALL_ORIGINS = True` (dev uniquement)
- **Allauth** : Login par email, vérification email `optional`
- **Pagination DRF** : `PageNumberPagination`, `PAGE_SIZE = 20`
- **Filtrage** : `DjangoFilterBackend`, `SearchFilter`, `OrderingFilter`
- **Media files** : `MEDIA_URL = '/media/'`, `MEDIA_ROOT = BASE_DIR / 'media'`

## Commandes Courantes

```bash
source env/bin/activate                 # activer le venv

python manage.py runserver              # serveur de dev
python manage.py makemigrations         # générer migrations
python manage.py migrate                # appliquer migrations
python manage.py createsuperuser        # créer admin
python manage.py shell                  # shell interactif
python manage.py test                   # tous les tests
python manage.py test apps.courses      # tests d'une app
python manage.py check                  # validation config
python manage.py showmigrations         # état des migrations
```

## Workflow de Développement

1. **Définir les modèles** dans `apps/<app>/models.py`
2. **Enregistrer les modèles** dans `apps/<app>/admin.py`
3. **Créer et appliquer les migrations** : `makemigrations` + `migrate`
4. **Implémenter les vues** (API views DRF) dans `apps/<app>/views.py`
5. **Définir les URLs** dans `apps/<app>/urls.py` (déjà inclus dans `urls.py` racine)
6. **Écrire les tests** dans `apps/<app>/tests.py`

## Apps à Implémenter (priorité logique)

| App | Modèles attendus |
|---|---|
| `courses` | `Course`, `Module`, `Lesson`, `Category`, `Tag` |
| `enrollments` | `Enrollment` (lien étudiant ↔ cours, statut, date) |
| `progress` | `ModuleProgress`, `LessonProgress` |
| `quizzes` | `Quiz`, `Question`, `Answer`, `Attempt`, `GradedAttempt` |
| `certificates` | `Certificate` (PDF via reportlab, lien ↔ cours terminé) |
| `dashboard` | Vues agrégées (stats, analytics) — pas de modèles propres |

## Points d'Attention

- **SECRET_KEY** et **DEBUG** utilisent `python-decouple` — créer un fichier `.env` pour la prod
- **CORS_ALLOW_ALL_ORIGINS = True** — restreindre en production
- **SQLite** — passer à PostgreSQL pour la prod
- **Aucune migration locale** n'existe encore pour les apps domain — il faut définir les modèles d'abord
- Les URLs de toutes les apps sont vides (`urlpatterns = []`)
- `authentication/views.py` et `authentication/urls.py` sont vides — dj-rest-auth fournit déjà les endpoints via la config allauth
