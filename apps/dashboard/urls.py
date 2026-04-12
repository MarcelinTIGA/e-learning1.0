"""
URLs de l'app 'dashboard'.

Routes :
    GET /api/dashboard/student/    — Dashboard apprenant
    GET /api/dashboard/formateur/  — Dashboard formateur
    GET /api/dashboard/admin/      — Dashboard admin

AMBIGUÏTÉ : Pourquoi pas de routes CRUD ?
  - Le dashboard est en lecture seule (pas de POST/PUT/DELETE)
  - Les données sont agrégées depuis les autres apps
  - On ne modifie pas le dashboard, on modifie les données sources
    (ex: s'inscrire à une formation → endpoint enrollments, pas dashboard)
"""

from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('student/', views.StudentDashboardView.as_view(), name='student-dashboard'),
    path('formateur/', views.FormateurDashboardView.as_view(), name='formateur-dashboard'),
    path('admin/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
]
