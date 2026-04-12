"""
URLs de l'app 'progress'.

Routes :
    GET  /api/progress/formations/                    — Toutes mes progressions
    GET  /api/progress/formations/<formation_id>/     — Progression dans une formation
    GET  /api/progress/formations/<formation_id>/resume/ — Reprendre où j'en étais
    POST /api/progress/lessons/<lesson_id>/complete/  — Marquer leçon terminée
    POST /api/progress/lessons/<lesson_id>/video/     — Sauvegarder position vidéo
    GET  /api/progress/lessons/<lesson_id>/           — État d'une leçon
"""

from django.urls import path

from . import views

app_name = 'progress'

urlpatterns = [
    # ── Progression par formation ─────────────────────────────────────────────
    path(
        'formations/',
        views.FormationProgressListView.as_view(),
        name='formation-progress-list',
    ),
    path(
        'formations/<int:formation_id>/',
        views.FormationProgressDetailView.as_view(),
        name='formation-progress-detail',
    ),
    path(
        'formations/<int:formation_id>/resume/',
        views.ResumeFormationView.as_view(),
        name='formation-resume',
    ),

    # ── Actions sur les leçons ────────────────────────────────────────────────
    # 'complete/' et 'video/' AVANT '<lesson_id>/' pour éviter les conflits de routing
    path(
        'lessons/<int:lesson_id>/complete/',
        views.MarkLessonCompleteView.as_view(),
        name='lesson-complete',
    ),
    path(
        'lessons/<int:lesson_id>/video/',
        views.SaveVideoPositionView.as_view(),
        name='lesson-video-position',
    ),
    path(
        'lessons/<int:lesson_id>/',
        views.LessonProgressDetailView.as_view(),
        name='lesson-progress-detail',
    ),
]
