"""
URLs de l'app 'quizzes'.

Routes formateur (gestion du contenu) :
    GET/POST   /api/quizzes/modules/<module_id>/quiz/           — Quiz d'un module
    GET/PATCH/DELETE /api/quizzes/<quiz_id>/                    — Détail quiz
    GET/POST   /api/quizzes/<quiz_id>/questions/                — Questions d'un quiz
    GET/PATCH/DELETE /api/quizzes/questions/<id>/               — Détail question
    GET/POST   /api/quizzes/questions/<question_id>/answers/    — Réponses d'une question
    GET/PATCH/DELETE /api/quizzes/answers/<id>/                 — Détail réponse

Routes apprenant (participation) :
    GET  /api/quizzes/<quiz_id>/attempt/    — Voir le quiz (sans bonnes réponses)
    POST /api/quizzes/<quiz_id>/submit/     — Soumettre ses réponses
    GET  /api/quizzes/<quiz_id>/history/    — Voir ses anciennes tentatives
"""

from django.urls import path

from . import views

app_name = 'quizzes'

urlpatterns = [
    # ── Gestion quiz par module (formateur) ───────────────────────────────
    path('modules/<int:module_id>/quiz/', views.QuizModuleView.as_view(), name='quiz-module'),
    path('<int:pk>/', views.QuizDetailView.as_view(), name='quiz-detail'),

    # ── Gestion des questions ──────────────────────────────────────────────
    path('<int:quiz_id>/questions/', views.QuestionListCreateView.as_view(), name='question-list'),
    path('questions/<int:pk>/', views.QuestionDetailView.as_view(), name='question-detail'),

    # ── Gestion des réponses ───────────────────────────────────────────────
    path('questions/<int:question_id>/answers/', views.AnswerListCreateView.as_view(), name='answer-list'),
    path('answers/<int:pk>/', views.AnswerDetailView.as_view(), name='answer-detail'),

    # ── Côté apprenant ─────────────────────────────────────────────────────
    # <quiz_id> : ID du quiz (distinct de <pk> pour éviter les conflits de nommage)
    path('<int:quiz_id>/attempt/', views.QuizAttemptView.as_view(), name='quiz-attempt'),
    path('<int:quiz_id>/submit/', views.QuizSubmitView.as_view(), name='quiz-submit'),
    path('<int:quiz_id>/history/', views.QuizHistoryView.as_view(), name='quiz-history'),
]
