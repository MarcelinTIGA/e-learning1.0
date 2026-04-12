"""
Tests pour l'app 'enrollments'.

Organisation :
  - EnrollmentCreateTest     : Création d'inscriptions (gratuit vs payant)
  - EnrollmentListTest       : Liste des inscriptions (apprenant vs admin)
  - EnrollmentDetailTest     : Détail d'une inscription
  - PaymentTest              : Statut du paiement
  - EnrollmentCancelTest     : Annulation d'inscription
  - WebhookTest              : Callback de paiement
"""

from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Category, Formation, Lesson, Module
from apps.users.models import User

from .models import Enrollment, Payment


def get_auth_client(user):
    """Crée un APIClient authentifié avec JWT."""
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


class EnrollmentCreateTest(APITestCase):
    """Tests de création d'inscriptions."""

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

        # Formation gratuite
        self.formation_gratuite = Formation.objects.create(
            formateur=self.formateur,
            categorie=self.categorie,
            titre='Python gratuit',
            description='Gratuit',
            prix=0,
            is_published=True,
        )

        # Formation payante
        self.formation_payante = Formation.objects.create(
            formateur=self.formateur,
            categorie=self.categorie,
            titre='Python avancé',
            description='Payant',
            prix=15000,
            is_published=True,
        )

        # Formation non publiée
        self.formation_brouillon = Formation.objects.create(
            formateur=self.formateur,
            titre='En préparation',
            description='...',
            is_published=False,
        )

    def test_enroll_free_formation(self):
        """Inscription à une formation gratuite → accès direct (ACTIVE)."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            '/api/enrollments/',
            {'formation_id': self.formation_gratuite.pk},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Enrollment.objects.filter(
            user=self.apprenant,
            formation=self.formation_gratuite,
            status=Enrollment.Status.ACTIVE,
        ).exists())
        # Pas de paiement pour une formation gratuite
        self.assertFalse(Payment.objects.filter(
            enrollment__user=self.apprenant,
        ).exists())

    def test_enroll_paid_formation(self):
        """Inscription à une formation payante → PENDING + Payment créé."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            '/api/enrollments/',
            {
                'formation_id': self.formation_payante.pk,
                'phone_number': '+237655000000',
                'provider': 'orange_money',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        enrollment = Enrollment.objects.get(
            user=self.apprenant,
            formation=self.formation_payante,
        )
        self.assertEqual(enrollment.status, Enrollment.Status.PENDING)
        # Vérifier le paiement
        self.assertTrue(Payment.objects.filter(
            enrollment=enrollment,
            status=Payment.Status.PENDING,
            amount=15000,
        ).exists())

    def test_enroll_paid_missing_phone(self):
        """Inscription payante sans téléphone → erreur 400."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            '/api/enrollments/',
            {
                'formation_id': self.formation_payante.pk,
                'provider': 'orange_money',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_enroll_paid_missing_provider(self):
        """Inscription payante sans opérateur → erreur 400."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            '/api/enrollments/',
            {
                'formation_id': self.formation_payante.pk,
                'phone_number': '+237655000000',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_enroll_draft_formation(self):
        """Inscription à une formation non publiée → erreur 400."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            '/api/enrollments/',
            {'formation_id': self.formation_brouillon.pk},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_enroll_formation_not_found(self):
        """Inscription à une formation inexistante → erreur 400."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            '/api/enrollments/',
            {'formation_id': 99999},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_enroll_duplicate(self):
        """Double inscription à la même formation → erreur."""
        client = get_auth_client(self.apprenant)
        # Première inscription
        client.post(
            '/api/enrollments/',
            {'formation_id': self.formation_gratuite.pk},
            format='json',
        )
        # Deuxième inscription → erreur
        response = client.post(
            '/api/enrollments/',
            {'formation_id': self.formation_gratuite.pk},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_enroll_unauthenticated(self):
        """Inscription sans authentification → erreur 401."""
        response = self.client.post(
            '/api/enrollments/',
            {'formation_id': self.formation_gratuite.pk},
            format='json',
        )
        self.assertEqual(response.status_code, 401)


class EnrollmentListTest(APITestCase):
    """Tests de liste des inscriptions."""

    def setUp(self):
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Jean', last_name='Apprenant',
        )
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Pass123!',
            first_name='Admin', last_name='Test',
            role=User.Role.ADMINISTRATEUR,
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
        # Inscriptions pour l'apprenant
        Enrollment.objects.create(
            user=self.apprenant, formation=self.formation,
            status=Enrollment.Status.ACTIVE,
        )

    def test_apprenant_sees_own_enrollments(self):
        """Un apprenant voit uniquement ses inscriptions."""
        client = get_auth_client(self.apprenant)
        response = client.get('/api/enrollments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_admin_sees_all_enrollments(self):
        """Un admin voit toutes les inscriptions."""
        # Créer une deuxième inscription
        apprenant2 = User.objects.create_user(
            email='autre@test.com', password='Pass123!',
            first_name='Alice', last_name='Autre',
        )
        Enrollment.objects.create(
            user=apprenant2, formation=self.formation,
            status=Enrollment.Status.ACTIVE,
        )

        client = get_auth_client(self.admin)
        response = client.get('/api/enrollments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)


class EnrollmentDetailTest(APITestCase):
    """Tests de détail d'une inscription."""

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
        self.enrollment = Enrollment.objects.create(
            user=self.apprenant, formation=self.formation,
            status=Enrollment.Status.ACTIVE,
        )

    def test_detail_owner(self):
        """Le propriétaire voit le détail de son inscription."""
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/enrollments/{self.enrollment.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['formation_titre'], 'Ma Formation')

    def test_detail_other_user(self):
        """Un autre utilisateur ne voit pas l'inscription."""
        client = get_auth_client(self.autre)
        response = client.get(f'/api/enrollments/{self.enrollment.pk}/')
        self.assertEqual(response.status_code, 404)


class PaymentTest(APITestCase):
    """Tests de consultation du statut de paiement."""

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
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            titre='Formation payante',
            description='...',
            prix=5000,
            is_published=True,
        )
        self.enrollment = Enrollment.objects.create(
            user=self.apprenant, formation=self.formation,
            status=Enrollment.Status.PENDING,
        )
        self.payment = Payment.objects.create(
            enrollment=self.enrollment,
            amount=5000,
            currency='XAF',
            provider=Payment.Provider.ORANGE,
            phone_number='+237655000000',
            status=Payment.Status.PENDING,
        )

    def test_payment_status(self):
        """L'apprenant peut voir le statut de son paiement."""
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/enrollments/{self.enrollment.pk}/payment/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(response.data['amount'], '5000.00')

    def test_payment_other_user(self):
        """Un autre utilisateur ne peut pas voir le paiement."""
        autre = User.objects.create_user(
            email='autre@test.com', password='Pass123!',
        )
        client = get_auth_client(autre)
        response = client.get(f'/api/enrollments/{self.enrollment.pk}/payment/')
        self.assertEqual(response.status_code, 404)

    def test_payment_free_formation(self):
        """Formation gratuite sans paiement → 404."""
        formation_gratuite = Formation.objects.create(
            formateur=self.formateur,
            titre='Formation gratuite',
            description='...',
            prix=0,
            is_published=True,
        )
        enrollment = Enrollment.objects.create(
            user=self.apprenant, formation=formation_gratuite,
            status=Enrollment.Status.ACTIVE,
        )
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/enrollments/{enrollment.pk}/payment/')
        self.assertEqual(response.status_code, 404)


class EnrollmentCancelTest(APITestCase):
    """Tests d'annulation d'inscription."""

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
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            titre='Ma Formation',
            description='...',
            is_published=True,
        )
        self.enrollment = Enrollment.objects.create(
            user=self.apprenant, formation=self.formation,
            status=Enrollment.Status.PENDING,
        )

    def test_cancel_own_enrollment(self):
        """L'apprenant peut annuler son inscription en attente."""
        client = get_auth_client(self.apprenant)
        response = client.post(f'/api/enrollments/{self.enrollment.pk}/cancel/')
        self.assertEqual(response.status_code, 200)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.CANCELLED)

    def test_cancel_other_user(self):
        """Un autre utilisateur ne peut pas annuler une inscription."""
        autre = User.objects.create_user(
            email='autre@test.com', password='Pass123!',
        )
        client = get_auth_client(autre)
        response = client.post(f'/api/enrollments/{self.enrollment.pk}/cancel/')
        self.assertEqual(response.status_code, 403)

    def test_cancel_completed(self):
        """Impossible d'annuler une inscription terminée."""
        self.enrollment.status = Enrollment.Status.COMPLETED
        self.enrollment.save()
        client = get_auth_client(self.apprenant)
        response = client.post(f'/api/enrollments/{self.enrollment.pk}/cancel/')
        self.assertEqual(response.status_code, 400)


class WebhookTest(APITestCase):
    """Tests du webhook de paiement."""

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
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            titre='Formation payante',
            description='...',
            prix=5000,
            is_published=True,
        )
        self.enrollment = Enrollment.objects.create(
            user=self.apprenant, formation=self.formation,
            status=Enrollment.Status.PENDING,
        )
        self.payment = Payment.objects.create(
            enrollment=self.enrollment,
            amount=5000,
            currency='XAF',
            provider=Payment.Provider.ORANGE,
            phone_number='+237655000000',
            status=Payment.Status.PENDING,
        )

    def test_webhook_success(self):
        """Webhook succès → inscription activée."""
        response = self.client.post(
            '/api/enrollments/webhook/',
            {
                'enrollment_id': self.enrollment.pk,
                'transaction_id': 'TX123456',
                'status': 'success',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.ACTIVE)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.transaction_id, 'TX123456')

    def test_webhook_failed(self):
        """Webhook échec → inscription annulée."""
        response = self.client.post(
            '/api/enrollments/webhook/',
            {
                'enrollment_id': self.enrollment.pk,
                'transaction_id': 'TX789',
                'status': 'failed',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.CANCELLED)

    def test_webhook_invalid_data(self):
        """Webhook avec données invalides → erreur 400."""
        response = self.client.post(
            '/api/enrollments/webhook/',
            {'bad': 'data'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_not_found(self):
        """Webhook pour une inscription inexistante → 404."""
        response = self.client.post(
            '/api/enrollments/webhook/',
            {
                'enrollment_id': 99999,
                'transaction_id': 'TX123',
                'status': 'success',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 404)

    def test_webhook_unauthenticated(self):
        """Le webhook est accessible sans authentification."""
        response = self.client.post(
            '/api/enrollments/webhook/',
            {
                'enrollment_id': self.enrollment.pk,
                'transaction_id': 'TX123',
                'status': 'success',
            },
            format='json',
        )
        # 200 ou 400 selon la validation, mais PAS 401/403
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)
