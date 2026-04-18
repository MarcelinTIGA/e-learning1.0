# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Django REST Framework backend for an e-learning platform (type Udemy, with academic logic). All 8 backend phases are implemented. The next step is a Flutter frontend that consumes this API.

## Environment Setup

```bash
source env/bin/activate   # Python 3.13.7 virtual environment
```

All dependencies are in `requirements.txt` and installed in `env/`. Key packages: Django 6.0.4, djangorestframework 3.17.1, djangorestframework-simplejwt 5.5.1, reportlab 4.4.0, django-allauth 65.15.1, django-filter 25.1, python-decouple 3.8.

## Common Commands

```bash
python manage.py runserver                        # start dev server
python manage.py makemigrations <app>             # after model changes
python manage.py migrate
python manage.py test                             # all tests (~150+)
python manage.py test apps.courses                # single app
python manage.py test apps.courses.tests.CatalogueTest.test_filter_by_niveau  # single test
python manage.py check                            # validate config
python manage.py createsuperuser
```

Settings use `python-decouple`: put `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` in a `.env` file at the project root.

## Architecture

### Data Model Hierarchy

```
User (UUID pk, email-based auth)
  └── UserProfile (1:1, auto-created via signal)

Category → Formation (formateur FK, prix, niveau, is_published)
                └── Module (order, unique_together formation+order)
                        ├── Lesson (content_type: video/pdf/text, is_preview, order)
                        └── Quiz (1:1, passing_score)
                                └── Question → Answer (is_correct hidden from students)

Enrollment (user+formation, status: pending/active/completed/cancelled)
  └── Payment (1:1, provider: orange_money/mtn_momo, Mobile Money stubs)

LessonProgress (user+lesson, completed, video_position_seconds)
FormationProgress (denormalized: completed_lessons, total_lessons, passed_quizzes, percentage, is_completed)

Certificate (UUID pk, verification_code, pdf_file, formation_titre_snapshot)
```

### Cross-App Event Flow (Signals)

- `post_save(User)` → auto-creates `UserProfile` (users/signals.py)
- `post_save(QuizAttempt)` → recalculates `FormationProgress` (progress/signals.py)
- `post_save(FormationProgress)` where `is_completed=True` → auto-generates `Certificate` PDF (certificates/signals.py)

Signals are connected in each app's `AppConfig.ready()`.

### Service Layer Pattern

Business logic lives in `services.py`, not in views. Views only validate input and delegate:

| Service | Key Methods |
|---|---|
| `quizzes/services.py` — `QuizGradingService` | `grade_submission()` — `@transaction.atomic`, `bulk_create` for AttemptAnswers, `Decimal` arithmetic |
| `enrollments/services.py` — `EnrollmentService` | `enroll()`, `confirm_payment()`, `cancel_enrollment()` |
| `progress/services.py` — `ProgressService` | `mark_lesson_complete()`, `save_video_position()`, `recalculate_formation_progress()` |
| `certificates/services.py` — `CertificateService` | `issue_certificate()`, PDF generation via reportlab |
| `dashboard/services.py` — `DashboardService` | `get_student_dashboard()`, `get_formateur_dashboard()`, `get_admin_dashboard()` |

### User Roles & Permissions

`User.role` ∈ {`apprenant`, `formateur`, `administrateur`}. `is_also_admin=True` lets a formateur also be admin. Key properties: `is_apprenant`, `is_formateur`, `is_administrateur`.

Custom permissions in `apps/users/permissions.py`: `IsFormateurOrAdmin`, `IsOwnerOrAdmin`.
Cross-app permission in `apps/enrollments/permissions.py`: `IsEnrolledAndPaid` — checks Enrollment status is active/completed for a given formation (traverses Lesson→Module→Formation hierarchy).

### Serializer Dual-View Pattern (quizzes)

Two serializer sets for the same data: formateur sees `is_correct` on answers; apprenant uses `QuizStudentSerializer` / `AnswerStudentSerializer` which exclude it.

### API Conventions

- All responses paginated: `{"count": N, "next": "...", "previous": "...", "results": [...]}`
- JWT Bearer tokens — 30min access, 7-day refresh with rotation and blacklist
- `get_serializer_class()` override returns different serializers for GET vs POST/PATCH
- `perform_create()` override injects FK from URL kwargs (e.g., `formateur=request.user`, `module=module`)
- `select_related` / `prefetch_related` used throughout to avoid N+1 queries

### Key URL Prefixes

```
/api/auth/          — register, login, logout, token/refresh, password/*
/api/users/         — me/, profile/
/api/courses/       — catalogue, formations CRUD, modules, lessons, categories
/api/quizzes/       — quiz CRUD, submit, history, attempt
/api/enrollments/   — enroll, confirm, cancel, webhook/
/api/progress/      — formations/<id>/, lessons/<id>/complete|video
/api/certificates/  — list, download, verify/<code>/
/api/dashboard/     — student/, formateur/, admin/
```

### Payment Integration

`enrollments/services.py` contains `OrangeMoneyGateway` and `MTNMoMoGateway` as stubs (always return success). Replace `initiate_payment()` and `verify_payment()` with real API calls when credentials are available. Webhook endpoint at `POST /api/enrollments/webhook/` is public (AllowAny) — add signature verification before production.

### PDF Certificates

`CertificateService.generate_pdf()` uses reportlab to produce a landscape A4 PDF stored in `media/certificates/pdfs/`. The `Certificate` model stores a `formation_titre_snapshot` at creation time so the document remains accurate if the formation is later renamed.

### Circular Import Prevention

`progress/services.py` and `quizzes/services.py` import from each other's apps inside function bodies (not at module level) to prevent circular import errors.
