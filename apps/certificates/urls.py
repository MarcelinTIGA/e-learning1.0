"""
URLs de l'app 'certificates'.

Routes :
    GET/POST  /api/certificates/                   — Liste + création
    GET       /api/certificates/<id>/              — Détail
    GET       /api/certificates/<id>/download/     — Télécharger PDF
    GET/POST  /api/certificates/verify/<code>/     — Vérifier un certificat

Note : 'verify/<code>/' est AVANT '<pk>/' pour éviter que Django
       interprète "verify" comme un UUID.
"""

from django.urls import path

from . import views

app_name = 'certificates'

urlpatterns = [
    # ── Vérification (avant <pk> pour éviter le conflit) ─────────────────────
    path('verify/<str:code>/', views.CertificateVerifyView.as_view(), name='verify'),

    # ── CRUD ─────────────────────────────────────────────────────────────────
    path('', views.CertificateListCreateView.as_view(), name='certificate-list'),
    path('<uuid:pk>/', views.CertificateDetailView.as_view(), name='certificate-detail'),
    path('<uuid:pk>/download/', views.CertificateDownloadView.as_view(), name='certificate-download'),
]
