# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Django-based e-learning platform backend API. The project is currently in the initial scaffolding phase — all domain apps exist but models, views, and business logic are yet to be implemented.

## Environment Setup

```bash
source env/bin/activate   # activate the Python 3.13.7 virtual environment
```

Dependencies (Django 6.0.4, asgiref, sqlparse) are installed in the `env/` directory. There is no `requirements.txt` yet.

## Common Commands

```bash
python manage.py runserver          # start development server
python manage.py makemigrations     # generate migration files after model changes
python manage.py migrate            # apply migrations to db.sqlite3
python manage.py createsuperuser    # create an admin user
python manage.py shell              # interactive Django shell
python manage.py test               # run all tests
python manage.py test apps.courses  # run tests for a single app
python manage.py check              # validate project configuration
```

## Architecture

The project uses a modular Django app structure under `apps/`. Each app owns a domain:

| App | Responsibility |
|---|---|
| `authentication` | Login, registration, session management |
| `users` | User profiles and preferences |
| `courses` | Course content, structure, metadata |
| `enrollments` | Student-course relationships |
| `progress` | Module completion tracking |
| `quizzes` | Questions, answers, grading |
| `certificates` | Certificate issuance on completion |
| `dashboard` | Analytics and reporting views |

URL routing starts at [elearning_backend/urls.py](elearning_backend/urls.py). Each app should register its own `urls.py` and include it there. The Django admin is available at `/admin/`.

Core settings are in [elearning_backend/settings.py](elearning_backend/settings.py). The database is SQLite at `db.sqlite3` (root directory). `DEBUG=True` and `SECRET_KEY` are currently hardcoded — use environment variables before any deployment.

## Development Workflow

1. Define models in `apps/<app>/models.py`
2. Register models in `apps/<app>/admin.py`
3. Run `makemigrations` + `migrate`
4. Implement views and wire up URL patterns
5. Write tests in `apps/<app>/tests.py`

No REST framework is installed yet — add `djangorestframework` if building a JSON API.
