"""
Tests pour l'app 'dashboard'.

Organisation :
  - StudentDashboardTest    : Stats apprenant
  - FormateurDashboardTest  : Stats formateur
  - AdminDashboardTest      : Stats administrateur
"""

from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Category, Formation, Lesson, Module
from apps.enrollments.models import Enrollment
from apps.users.models import User

from .services import DashboardService


def get_auth_client(user, client=None):
    """Crée un APIClient authentifié avec JWT."""
    from rest_framework.test import APIClient
    if client is None:
        client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


class StudentDashboardTest(APITestCase):
    """Tests du dashboard apprenant."""

    def setUp(self):
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Jean', last_name='Apprenant',
        )
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Marie', last_name='Formatrice',
            role=User.Role.FORMATEUR,
        )
        self.categorie = Category.objects.create(name='Python')
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            categorie=self.categorie,
            titre='Python pour débutants',
            description='...',
            is_published=True,
        )
        self.enrollment = Enrollment.objects.create(
            user=self.apprenant, formation=self.formation,
            status=Enrollment.Status.ACTIVE,
        )

    def test_student_dashboard_data(self):
        """Le service retourne les bonnes données."""
        data = DashboardService.get_student_dashboard(self.apprenant)
        self.assertEqual(data['total_enrollments'], 1)
        self.assertEqual(data['active_enrollments'], 1)
        self.assertEqual(data['completed_enrollments'], 0)
        self.assertEqual(data['certificates_count'], 0)

    def test_student_dashboard_api(self):
        """L'API retourne les données du dashboard."""
        client = get_auth_client(self.apprenant)
        response = client.get('/api/dashboard/student/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_enrollments', response.data)
        self.assertIn('active_enrollments', response.data)
        self.assertIn('certificates_count', response.data)

    def test_student_dashboard_unauthenticated(self):
        """Un utilisateur non authentifié ne peut pas accéder."""
        response = self.client.get('/api/dashboard/student/')
        self.assertEqual(response.status_code, 401)

    def test_student_dashboard_empty(self):
        """Un apprenant sans inscriptions a des compteurs à 0."""
        nouvel = User.objects.create_user(
            email='nouveau@test.com', password='Pass123!',
            first_name='Nouveau', last_name='User',
        )
        client = get_auth_client(nouvel)
        response = client.get('/api/dashboard/student/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_enrollments'], 0)
        self.assertEqual(response.data['current_progress'], [])


class FormateurDashboardTest(APITestCase):
    """Tests du dashboard formateur."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Marie', last_name='Formatrice',
            role=User.Role.FORMATEUR,
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Jean', last_name='Apprenant',
        )
        self.categorie = Category.objects.create(name='Python')
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            categorie=self.categorie,
            titre='Python avancé',
            description='...',
            prix=10000,
            is_published=True,
        )
        Enrollment.objects.create(
            user=self.apprenant, formation=self.formation,
            status=Enrollment.Status.ACTIVE,
        )

    def test_formateur_dashboard_data(self):
        """Le service retourne les bonnes données."""
        data = DashboardService.get_formateur_dashboard(self.formateur)
        self.assertEqual(data['total_formations'], 1)
        self.assertEqual(data['published_formations'], 1)
        self.assertEqual(data['total_students'], 1)

    def test_formateur_dashboard_api(self):
        """L'API retourne les données du dashboard."""
        client = get_auth_client(self.formateur)
        response = client.get('/api/dashboard/formateur/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_formations', response.data)
        self.assertIn('formations_stats', response.data)

    def test_formateur_dashboard_unauthenticated(self):
        """Un utilisateur non authentifié ne peut pas accéder."""
        response = self.client.get('/api/dashboard/formateur/')
        self.assertEqual(response.status_code, 401)

    def test_apprenant_cannot_access_formateur_dashboard(self):
        """Un apprenant ne peut pas accéder au dashboard formateur."""
        client = get_auth_client(self.apprenant)
        response = client.get('/api/dashboard/formateur/')
        self.assertEqual(response.status_code, 403)

    def test_formateur_empty_formations(self):
        """Un formateur sans formations a des compteurs à 0."""
        nouveau = User.objects.create_user(
            email='nouveau@test.com', password='Pass123!',
            first_name='Nouveau', last_name='Formateur',
            role=User.Role.FORMATEUR,
        )
        client = get_auth_client(nouveau)
        response = client.get('/api/dashboard/formateur/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_formations'], 0)
        self.assertEqual(response.data['total_students'], 0)


class AdminDashboardTest(APITestCase):
    """Tests du dashboard administrateur."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Pass123!',
            first_name='Admin', last_name='Test',
            role=User.Role.ADMINISTRATEUR,
            is_staff=True,
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Jean', last_name='Apprenant',
        )
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Marie', last_name='Formatrice',
            role=User.Role.FORMATEUR,
        )

    def test_admin_dashboard_data(self):
        """Le service retourne les bonnes données."""
        data = DashboardService.get_admin_dashboard()
        self.assertEqual(data['total_users'], 3)
        self.assertEqual(data['total_apprenants'], 1)
        self.assertEqual(data['total_formateurs'], 1)

    def test_admin_dashboard_api(self):
        """L'API retourne les données du dashboard."""
        client = get_auth_client(self.admin)
        response = client.get('/api/dashboard/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_users', response.data)
        self.assertIn('total_formations', response.data)
        self.assertIn('certificates_issued', response.data)

    def test_admin_dashboard_unauthenticated(self):
        """Un utilisateur non authentifié ne peut pas accéder."""
        response = self.client.get('/api/dashboard/admin/')
        self.assertEqual(response.status_code, 401)

    def test_apprenant_cannot_access_admin_dashboard(self):
        """Un apprenant ne peut pas accéder au dashboard admin."""
        client = get_auth_client(self.apprenant)
        response = client.get('/api/dashboard/admin/')
        self.assertEqual(response.status_code, 403)

    def test_formateur_cannot_access_admin_dashboard(self):
        """Un formateur ne peut pas accéder au dashboard admin."""
        client = get_auth_client(self.formateur)
        response = client.get('/api/dashboard/admin/')
        self.assertEqual(response.status_code, 403)
