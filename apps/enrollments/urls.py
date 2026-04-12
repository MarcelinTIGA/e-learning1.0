"""
URLs de l'app 'enrollments'.

Routes :
    POST/GET  /api/enrollments/                         — Liste + création inscriptions
    GET       /api/enrollments/<id>/                    — Détail inscription
    GET       /api/enrollments/<enrollment_id>/payment/ — Statut paiement
    POST      /api/enrollments/<enrollment_id>/confirm/ — Confirmer (admin)
    POST      /api/enrollments/<enrollment_id>/cancel/  — Annuler
    POST      /api/enrollments/webhook/                 — Callback opérateur

Note : 'webhook/' est AVANT '<id>/' pour éviter que Django interprète
       "webhook" comme un entier (ce qui causerait une erreur 404).
"""

from django.urls import path

from . import views

app_name = 'enrollments'

urlpatterns = [
    # ── Webhook en premier (avant les routes avec <int:>) ────────────────────
    # IMPORTANT : doit être AVANT les routes avec <int:enrollment_id>
    # car Django lit les patterns dans l'ordre et s'arrête au premier match.
    # Si on met <int:> avant, Django essaierait de convertir "webhook" en int → erreur.
    path('webhook/', views.PaymentWebhookView.as_view(), name='payment-webhook'),

    # ── Inscriptions ──────────────────────────────────────────────────────────
    path('', views.EnrollmentListCreateView.as_view(), name='enrollment-list'),
    path('<int:pk>/', views.EnrollmentDetailView.as_view(), name='enrollment-detail'),

    # ── Actions sur une inscription spécifique ────────────────────────────────
    path('<int:enrollment_id>/payment/', views.PaymentDetailView.as_view(), name='payment-detail'),
    path('<int:enrollment_id>/confirm/', views.ConfirmPaymentView.as_view(), name='enrollment-confirm'),
    path('<int:enrollment_id>/cancel/',  views.CancelEnrollmentView.as_view(), name='enrollment-cancel'),
]
