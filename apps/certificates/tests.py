"""
Tests pour l'app 'certificates'.

Organisation :
  - CertificateAutoGenerationTest : le signal crée le certificat à 100%
  - CertificateManualCreateTest   : création manuelle par admin
  - CertificateDownloadTest       : téléchargement du PDF
  - CertificateVerifyTest         : vérification par code
"""

from io import BytesIO

from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Category, Formation, Lesson, Module
from apps.progress.models import FormationProgress, LessonProgress
from apps.users.models import User

from .models import Certificate


def get_auth_client(user):
    """Crée un APIClient authentifié avec JWT."""
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


class CertificateAutoGenerationTest(APITestCase):
    """Tests de la génération automatique de certificats."""

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
            description='Apprenez Python',
            prix=0,  # Gratuite pour simplifier le test
            is_published=True,
        )
        self.module = Module.objects.create(
            formation=self.formation,
            titre='Module 1',
            order=1,
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            titre='Leçon 1',
            content_type=Lesson.ContentType.TEXT,
            text_content='Bonjour',
            order=1,
        )
        # Créer la progression
        self.progress = FormationProgress.objects.create(
            user=self.apprenant,
            formation=self.formation,
        )

    def test_certificate_created_when_completed(self):
        """Un certificat est automatiquement créé quand is_completed = True."""
        self.progress.is_completed = True
        self.progress.percentage = 100
        self.progress.completed_lessons = 1
        self.progress.total_lessons = 1
        self.progress.save()

        self.assertTrue(
            Certificate.objects.filter(
                user=self.apprenant,
                formation=self.formation,
            ).exists()
        )

    def test_certificate_not_created_when_not_completed(self):
        """Pas de certificat si la formation n'est pas terminée."""
        self.progress.is_completed = False
        self.progress.percentage = 50
        self.progress.save()

        self.assertFalse(
            Certificate.objects.filter(
                user=self.apprenant,
                formation=self.formation,
            ).exists()
        )

    def test_certificate_has_pdf(self):
        """Le certificat généré a un fichier PDF."""
        self.progress.is_completed = True
        self.progress.percentage = 100
        self.progress.completed_lessons = 1
        self.progress.total_lessons = 1
        self.progress.save()

        cert = Certificate.objects.get(user=self.apprenant, formation=self.formation)
        self.assertTrue(bool(cert.pdf_file))

    def test_certificate_has_verification_code(self):
        """Le certificat a un code de vérification au bon format."""
        self.progress.is_completed = True
        self.progress.percentage = 100
        self.progress.completed_lessons = 1
        self.progress.total_lessons = 1
        self.progress.save()

        cert = Certificate.objects.get(user=self.apprenant, formation=self.formation)
        self.assertTrue(cert.verification_code.startswith('CERT-'))
        # Format: CERT-YYYY-XXXXXXXX (18 chars : 5 + 5 + 8)
        self.assertEqual(len(cert.verification_code), 18)

    def test_no_duplicate_certificate(self):
        """Le signal ne crée pas de doublon si is_completed est remis à True."""
        self.progress.is_completed = True
        self.progress.percentage = 100
        self.progress.completed_lessons = 1
        self.progress.total_lessons = 1
        self.progress.save()

        # Sauvegarder à nouveau (déclenche le signal une deuxième fois)
        self.progress.save()

        count = Certificate.objects.filter(
            user=self.apprenant,
            formation=self.formation,
        ).count()
        self.assertEqual(count, 1)


class CertificateManualCreateTest(APITestCase):
    """Tests de création manuelle de certificats."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Pass123!',
            first_name='Admin', last_name='Test',
            role=User.Role.ADMINISTRATEUR,
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
        self.categorie = Category.objects.create(name='Python')
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            categorie=self.categorie,
            titre='Python avancé',
            description='Python avancé',
            is_published=True,
        )

    def test_admin_can_create_certificate(self):
        """Un admin peut créer manuellement un certificat."""
        # Créer la progression pour satisfaire la vérification du service
        from apps.progress.models import FormationProgress
        progress = FormationProgress.objects.create(
            user=self.apprenant, formation=self.formation,
            is_completed=True, percentage=100,
            completed_lessons=1, total_lessons=1,
        )
        # Le signal a déjà créé un certificat → on le supprime pour tester la création manuelle
        Certificate.objects.filter(user=self.apprenant, formation=self.formation).delete()

        client = get_auth_client(self.admin)
        response = client.post(
            '/api/certificates/',
            {
                'user_id': str(self.apprenant.pk),
                'formation_id': self.formation.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Certificate.objects.filter(user=self.apprenant).exists())

    def test_apprenant_cannot_create_certificate(self):
        """Un apprenant ne peut pas créer de certificat manuellement."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            '/api/certificates/',
            {
                'user_id': str(self.apprenant.pk),
                'formation_id': self.formation.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_list_certificates_apprenant(self):
        """Un apprenant ne voit que ses propres certificats."""
        # Créer un certificat pour l'apprenant
        FormationProgress.objects.create(
            user=self.apprenant, formation=self.formation,
            is_completed=True, percentage=100,
        )

        client = get_auth_client(self.apprenant)
        response = client.get('/api/certificates/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)


class CertificateDownloadTest(APITestCase):
    """Tests de téléchargement du PDF."""

    def setUp(self):
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Jean', last_name='Apprenant',
        )
        self.autre = User.objects.create_user(
            email='autre@test.com', password='Pass123!',
            first_name='Autre', last_name='User',
        )
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Marie', last_name='Formatrice',
            role=User.Role.FORMATEUR,
        )
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            titre='Ma Formation',
            description='...',
            is_published=True,
        )
        # Créer le certificat avec PDF
        self.progress = FormationProgress.objects.create(
            user=self.apprenant, formation=self.formation,
            is_completed=True, percentage=100,
        )
        self.certificate = Certificate.objects.get(
            user=self.apprenant, formation=self.formation
        )

    def test_download_certificate_owner(self):
        """Le propriétaire peut télécharger son certificat."""
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/certificates/{self.certificate.pk}/download/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'].startswith('attachment'), True)

    def test_download_certificate_other_user(self):
        """Un autre utilisateur ne peut pas télécharger le certificat."""
        client = get_auth_client(self.autre)
        response = client.get(f'/api/certificates/{self.certificate.pk}/download/')
        self.assertEqual(response.status_code, 404)


class CertificateVerifyTest(APITestCase):
    """Tests de vérification de certificats."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Marie', last_name='Formatrice',
            role=User.Role.FORMATEUR,
        )
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            titre='Ma Formation',
            description='...',
            is_published=True,
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Jean', last_name='Apprenant',
        )
        # Créer le certificat
        self.progress = FormationProgress.objects.create(
            user=self.apprenant, formation=self.formation,
            is_completed=True, percentage=100,
        )
        self.certificate = Certificate.objects.get(
            user=self.apprenant, formation=self.formation
        )

    def test_verify_valid_code(self):
        """Un code valide retourne les infos du certificat."""
        response = self.client.post(
            f'/api/certificates/verify/{self.certificate.verification_code}/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_valid'])
        self.assertEqual(response.data['certificate']['formation'], self.formation.titre)

    def test_verify_invalid_code(self):
        """Un code invalide retourne une erreur."""
        response = self.client.post('/api/certificates/verify/CERT-2024-INVALID/')
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.data['is_valid'])

    def test_verify_unauthenticated(self):
        """N'importe qui peut vérifier un certificat (pas d'auth requise)."""
        response = self.client.post(
            f'/api/certificates/verify/{self.certificate.verification_code}/'
        )
        self.assertEqual(response.status_code, 200)
