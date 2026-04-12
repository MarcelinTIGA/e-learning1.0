"""
URLs de l'app 'courses'.

Organisation des routes :
  Catalogue public (sans authentification) :
    GET  /api/courses/                              → Liste formations publiées
    GET  /api/courses/<id>/                         → Détail d'une formation

  Gestion des formations (formateur/admin) :
    GET  /api/courses/manage/                       → Mes formations
    POST /api/courses/manage/                       → Créer une formation
    GET/PUT/PATCH/DELETE /api/courses/manage/<id>/  → Détail / modification

  Catégories :
    GET  /api/courses/categories/                   → Liste des catégories
    POST /api/courses/categories/                   → Créer (admin)
    GET/PUT/PATCH/DELETE /api/courses/categories/<id>/

  Modules (imbriqués dans une formation) :
    GET  /api/courses/<formation_pk>/modules/       → Lister les modules
    POST /api/courses/<formation_pk>/modules/       → Ajouter un module
    GET/PUT/PATCH/DELETE /api/courses/modules/<id>/ → Modifier un module

  Leçons (imbriquées dans un module) :
    GET  /api/courses/modules/<module_pk>/lessons/       → Lister les leçons
    POST /api/courses/modules/<module_pk>/lessons/       → Ajouter une leçon
    GET/PUT/PATCH/DELETE /api/courses/lessons/<id>/      → Modifier une leçon
"""

from django.urls import path

from . import views

app_name = 'courses'

urlpatterns = [
    # ── Catalogue public ───────────────────────────────────────────────────
    path('', views.CatalogueView.as_view(), name='catalogue'),
    path('<int:pk>/', views.FormationPublicDetailView.as_view(), name='formation-detail'),

    # ── Gestion des formations (formateur/admin) ───────────────────────────
    path('manage/', views.FormationManageListCreateView.as_view(), name='formation-manage-list'),
    path('manage/<int:pk>/', views.FormationManageDetailView.as_view(), name='formation-manage-detail'),

    # ── Catégories ─────────────────────────────────────────────────────────
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),

    # ── Modules (imbriqués dans une formation) ─────────────────────────────
    # <formation_pk> : ID de la formation parente, récupéré dans la view via self.kwargs
    path('<int:formation_pk>/modules/', views.ModuleListCreateView.as_view(), name='module-list'),
    path('modules/<int:pk>/', views.ModuleDetailView.as_view(), name='module-detail'),

    # ── Leçons (imbriquées dans un module) ─────────────────────────────────
    # <module_pk> : ID du module parent, récupéré dans la view via self.kwargs
    path('modules/<int:module_pk>/lessons/', views.LessonListCreateView.as_view(), name='lesson-list'),
    path('lessons/<int:pk>/', views.LessonDetailView.as_view(), name='lesson-detail'),
]
