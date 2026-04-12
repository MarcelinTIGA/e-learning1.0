"""
Views pour l'app 'dashboard'.

Endpoints disponibles :
    GET /api/dashboard/student/     — Dashboard apprenant
    GET /api/dashboard/formateur/   — Dashboard formateur
    GET /api/dashboard/admin/       — Dashboard administrateur

AMBIGUÏTÉ : Pourquoi 3 endpoints séparés au lieu d'un seul /api/dashboard/ ?
  - Un seul endpoint nécessiterait de détecter le rôle et retourner des données différentes
  - Avec 3 endpoints :
    1. Chaque vue a une permission claire (IsAuthenticated + rôle)
    2. Le frontend appelle uniquement l'endpoint du rôle de l'utilisateur
    3. Plus facile à documenter et tester
  - Inconvénient : si un utilisateur a plusieurs rôles, il doit appeler plusieurs endpoints
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsFormateurOrAdmin

from .serializers import (
    AdminDashboardSerializer,
    FormateurDashboardSerializer,
    StudentDashboardSerializer,
)
from .services import DashboardService


class StudentDashboardView(APIView):
    """
    GET /api/dashboard/student/
    Tableau de bord de l'apprenant.
    Affiche sa progression, ses formations en cours, ses certificats.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # AMBIGUÏTÉ : Faut-il restreindre aux apprenants uniquement ?
        #   - Non : un formateur ou admin peut aussi être apprenant sur d'autres formations
        #   - On retourne les données de l'utilisateur connecté, quel que soit son rôle
        data = DashboardService.get_student_dashboard(request.user)
        serializer = StudentDashboardSerializer(data)
        return Response(serializer.data)


class FormateurDashboardView(APIView):
    """
    GET /api/dashboard/formateur/
    Tableau de bord du formateur.
    Affiche les stats de ses formations (inscrits, revenus, etc.).
    """

    # Seuls les formateurs et admins peuvent voir ce dashboard
    permission_classes = [IsFormateurOrAdmin]

    def get(self, request):
        data = DashboardService.get_formateur_dashboard(request.user)
        serializer = FormateurDashboardSerializer(data)
        return Response(serializer.data)


class AdminDashboardView(APIView):
    """
    GET /api/dashboard/admin/
    Tableau de bord administrateur.
    Affiche les stats globales de la plateforme.
    """

    # Réservé aux administrateurs
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        data = DashboardService.get_admin_dashboard()
        serializer = AdminDashboardSerializer(data)
        return Response(serializer.data)
