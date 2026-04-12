"""
Tests pour l'app 'enrollments'.

Organisation des tests :
    - EnrollmentServiceTest    : logique métier (service) — inscriptions, paiements
    - IsEnrolledAndPaidTest    : permission cross-app
    - EnrollmentAPITest        : endpoints REST (inscription, liste, détail)
    - PaymentAPITest           : endpoint statut paiement
    - WebhookAPITest           : callback opérateur (webhook)
    - ConfirmCancelAPITest     : confirmation/annulation manuelle

Total : ~26 tests
"""

from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Category, Formation
from apps.users.models import User
from django.test import TestCase

from .models import Enrollment, Payment
from .services import EnrollmentService


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_auth_client(user):
    """
    Crée un client API authentifié avec un JWT valide pour cet utilisateur.

    Utilisé dans tous les tests qui nécessitent un utilisateur connecté.
    """
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    # On utilise l'access token pour les requêtes API
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


def create_formation(formateur, titre='Formation Test', prix=0, is_published=True):
    """
    Crée une formation de test avec les valeurs par défaut.

    Args:
        formateur:    Le formateur propriétaire
        titre:        Titre de la formation
        prix:         Prix en XAF (0 = gratuite)
        is_published: Si True, la formation est visible et ouverte aux inscriptions
    """
    # get_or_create évite l'erreur UNIQUE si la catégorie existe déjà dans le même test
    category, _ = Category.objects.get_or_create(name='Cat Test', defaults={'slug': 'cat-test'})
    return Formation.objects.create(
        formateur=formateur,
        categorie=category,
        titre=titre,
        description='Description test',
        prix=Decimal(str(prix)),
        niveau=Formation.Level.DEBUTANT,
        is_published=is_published,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TESTS DU SERVICE MÉTIER
# ─────────────────────────────────────────────────────────────────────────────

class EnrollmentServiceTest(TestCase):
    """
    Teste la logique métier d'inscription dans services.py.

    Ces tests vérifient les règles sans passer par HTTP (plus rapide).
    """

    def setUp(self):
        """Crée les utilisateurs et formation réutilisés dans tous les tests."""
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='pass', role=User.Role.FORMATEUR
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='pass', role=User.Role.APPRENANT
        )

    def test_inscription_formation_gratuite(self):
        """
        Une inscription à une formation gratuite doit être ACTIVE immédiatement.
        Pas de Payment créé pour une formation gratuite.
        """
        formation = create_formation(self.formateur, prix=0)

        enrollment = EnrollmentService.enroll(self.apprenant, formation.pk)

        # L'inscription doit être active dès le départ
        self.assertEqual(enrollment.status, Enrollment.Status.ACTIVE)
        # Aucun paiement ne doit être créé pour une formation gratuite
        self.assertFalse(hasattr(enrollment, 'payment') and Payment.objects.filter(enrollment=enrollment).exists())

    def test_inscription_formation_payante_orange_money(self):
        """
        Une inscription à une formation payante doit créer un Payment(PENDING)
        et laisser l'Enrollment en statut PENDING.
        """
        formation = create_formation(self.formateur, prix=5000)

        enrollment = EnrollmentService.enroll(
            self.apprenant,
            formation.pk,
            phone_number='+237655000000',
            provider='orange_money',
        )

        # L'inscription doit être en attente du paiement
        self.assertEqual(enrollment.status, Enrollment.Status.PENDING)

        # Un paiement doit avoir été créé
        payment = Payment.objects.get(enrollment=enrollment)
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.provider, 'orange_money')
        self.assertEqual(payment.amount, Decimal('5000'))

        # Le transaction_id doit être renseigné (simulé par le stub)
        self.assertIn('ORANGE_STUB', payment.transaction_id)

    def test_inscription_formation_payante_mtn_momo(self):
        """Même test qu'Orange Money mais avec MTN MoMo."""
        formation = create_formation(self.formateur, prix=3000)

        enrollment = EnrollmentService.enroll(
            self.apprenant,
            formation.pk,
            phone_number='+237677000000',
            provider='mtn_momo',
        )

        payment = Payment.objects.get(enrollment=enrollment)
        self.assertEqual(payment.provider, 'mtn_momo')
        self.assertIn('MTN_STUB', payment.transaction_id)

    def test_double_inscription_impossible(self):
        """
        Un apprenant ne peut pas s'inscrire deux fois à la même formation.
        La deuxième tentative doit lever une ValueError.
        """
        formation = create_formation(self.formateur, prix=0)

        # Première inscription : OK
        EnrollmentService.enroll(self.apprenant, formation.pk)

        # Deuxième inscription : doit échouer
        with self.assertRaises(ValueError) as ctx:
            EnrollmentService.enroll(self.apprenant, formation.pk)

        self.assertIn('déjà inscrit', str(ctx.exception).lower())

    def test_inscription_formation_non_publiee_impossible(self):
        """
        On ne peut pas s'inscrire à une formation non publiée.
        """
        formation = create_formation(self.formateur, prix=0, is_published=False)

        with self.assertRaises(ValueError) as ctx:
            EnrollmentService.enroll(self.apprenant, formation.pk)

        self.assertIn('pas encore disponible', str(ctx.exception).lower())

    def test_inscription_payante_sans_telephone_echoue(self):
        """
        Pour une formation payante, phone_number et provider sont obligatoires.
        Oublier l'un d'eux doit lever une ValueError.
        """
        formation = create_formation(self.formateur, prix=5000)

        with self.assertRaises(ValueError) as ctx:
            EnrollmentService.enroll(self.apprenant, formation.pk)

        self.assertIn('numéro de téléphone', str(ctx.exception).lower())

    def test_confirmation_paiement(self):
        """
        Confirmer un paiement doit passer l'inscription de PENDING à ACTIVE.
        """
        formation = create_formation(self.formateur, prix=5000)
        enrollment = EnrollmentService.enroll(
            self.apprenant, formation.pk,
            phone_number='+237655000000', provider='orange_money'
        )

        # Confirmer le paiement (simule le webhook de l'opérateur)
        enrollment = EnrollmentService.confirm_payment(enrollment.pk)

        self.assertEqual(enrollment.status, Enrollment.Status.ACTIVE)
        self.assertEqual(enrollment.payment.status, Payment.Status.SUCCESS)

    def test_annulation_inscription(self):
        """
        Annuler une inscription doit passer son statut à CANCELLED.
        Si un paiement PENDING existe, il doit passer à FAILED.
        """
        formation = create_formation(self.formateur, prix=5000)
        enrollment = EnrollmentService.enroll(
            self.apprenant, formation.pk,
            phone_number='+237655000000', provider='orange_money'
        )

        enrollment = EnrollmentService.cancel_enrollment(enrollment.pk)

        self.assertEqual(enrollment.status, Enrollment.Status.CANCELLED)
        self.assertEqual(enrollment.payment.status, Payment.Status.FAILED)

    def test_confirmation_inscription_deja_active_echoue(self):
        """
        Confirmer une inscription déjà active doit lever une ValueError.
        Évite la double confirmation accidentelle.
        """
        formation = create_formation(self.formateur, prix=5000)
        enrollment = EnrollmentService.enroll(
            self.apprenant, formation.pk,
            phone_number='+237655000000', provider='orange_money'
        )
        EnrollmentService.confirm_payment(enrollment.pk)

        # Tenter de confirmer à nouveau
        with self.assertRaises(ValueError):
            EnrollmentService.confirm_payment(enrollment.pk)


# ─────────────────────────────────────────────────────────────────────────────
# TESTS DE LA PERMISSION IsEnrolledAndPaid
# ─────────────────────────────────────────────────────────────────────────────

class IsEnrolledAndPaidTest(TestCase):
    """Teste la permission cross-app IsEnrolledAndPaid."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur2@test.com', password='pass', role=User.Role.FORMATEUR
        )
        self.apprenant = User.objects.create_user(
            email='apprenant2@test.com', password='pass', role=User.Role.APPRENANT
        )
        self.formation = create_formation(self.formateur, prix=0)

    def test_apprenant_inscrit_actif_a_acces(self):
        """Un apprenant avec inscription ACTIVE doit avoir accès."""
        from .permissions import IsEnrolledAndPaid

        # Créer une inscription active
        Enrollment.objects.create(
            user=self.apprenant,
            formation=self.formation,
            status=Enrollment.Status.ACTIVE,
        )

        perm = IsEnrolledAndPaid()
        # _check_enrollment retourne True si l'inscription est active
        self.assertTrue(perm._check_enrollment(self.apprenant, self.formation.pk))

    def test_apprenant_non_inscrit_naccede_pas(self):
        """Un apprenant sans inscription ne doit pas avoir accès."""
        from .permissions import IsEnrolledAndPaid

        perm = IsEnrolledAndPaid()
        self.assertFalse(perm._check_enrollment(self.apprenant, self.formation.pk))

    def test_apprenant_inscription_pending_naccede_pas(self):
        """Une inscription PENDING (paiement non confirmé) ne donne pas accès."""
        from .permissions import IsEnrolledAndPaid

        Enrollment.objects.create(
            user=self.apprenant,
            formation=self.formation,
            status=Enrollment.Status.PENDING,
        )

        perm = IsEnrolledAndPaid()
        self.assertFalse(perm._check_enrollment(self.apprenant, self.formation.pk))


# ─────────────────────────────────────────────────────────────────────────────
# TESTS DES ENDPOINTS API
# ─────────────────────────────────────────────────────────────────────────────

class EnrollmentAPITest(TestCase):
    """Teste les endpoints /api/enrollments/."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='form3@test.com', password='pass', role=User.Role.FORMATEUR
        )
        self.apprenant = User.objects.create_user(
            email='app3@test.com', password='pass', role=User.Role.APPRENANT
        )
        self.autre_apprenant = User.objects.create_user(
            email='autre@test.com', password='pass', role=User.Role.APPRENANT
        )
        self.admin = User.objects.create_user(
            email='admin3@test.com', password='pass',
            role=User.Role.FORMATEUR, is_also_admin=True
        )
        self.formation_gratuite = create_formation(self.formateur, titre='Gratuite', prix=0)
        self.formation_payante  = create_formation(self.formateur, titre='Payante', prix=10000)

    def test_inscription_formation_gratuite(self):
        """POST /api/enrollments/ → inscription gratuite = ACTIVE."""
        client = get_auth_client(self.apprenant)
        url = reverse('enrollments:enrollment-list')

        response = client.post(url, {'formation_id': self.formation_gratuite.pk}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'active')

    def test_inscription_formation_payante(self):
        """POST /api/enrollments/ → inscription payante = PENDING + paiement initié."""
        client = get_auth_client(self.apprenant)
        url = reverse('enrollments:enrollment-list')

        response = client.post(url, {
            'formation_id': self.formation_payante.pk,
            'phone_number': '+237655000000',
            'provider': 'orange_money',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')
        # Le paiement doit être inclus dans la réponse
        self.assertIsNotNone(response.data['payment'])

    def test_non_authentifie_ne_peut_pas_sinscrire(self):
        """POST sans JWT → 401 Unauthorized."""
        client = APIClient()  # Pas de credentials
        url = reverse('enrollments:enrollment-list')

        response = client.post(url, {'formation_id': self.formation_gratuite.pk}, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_double_inscription_retourne_400(self):
        """Tenter de s'inscrire deux fois → 400 Bad Request."""
        client = get_auth_client(self.apprenant)
        url = reverse('enrollments:enrollment-list')

        # Première inscription
        client.post(url, {'formation_id': self.formation_gratuite.pk}, format='json')
        # Deuxième tentative
        response = client.post(url, {'formation_id': self.formation_gratuite.pk}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_apprenant_voit_uniquement_ses_inscriptions(self):
        """GET /api/enrollments/ → l'apprenant ne voit que ses inscriptions."""
        # Créer une inscription pour l'apprenant
        Enrollment.objects.create(user=self.apprenant, formation=self.formation_gratuite, status='active')
        # Créer une inscription pour un autre apprenant
        formation2 = create_formation(self.formateur, titre='Formation 2', prix=0)
        Enrollment.objects.create(user=self.autre_apprenant, formation=formation2, status='active')

        client = get_auth_client(self.apprenant)
        url = reverse('enrollments:enrollment-list')
        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # L'apprenant ne voit que SES inscriptions (1 sur 2)
        self.assertEqual(response.data['count'], 1)

    def test_admin_voit_toutes_inscriptions(self):
        """GET /api/enrollments/ → l'admin voit toutes les inscriptions."""
        Enrollment.objects.create(user=self.apprenant, formation=self.formation_gratuite, status='active')
        formation2 = create_formation(self.formateur, titre='Formation 3', prix=0)
        Enrollment.objects.create(user=self.autre_apprenant, formation=formation2, status='active')

        client = get_auth_client(self.admin)
        url = reverse('enrollments:enrollment-list')
        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_apprenant_ne_peut_voir_inscription_dun_autre(self):
        """GET /api/enrollments/<id>/ → 404 si l'inscription appartient à quelqu'un d'autre."""
        # Inscription appartenant à autre_apprenant
        enrollment = Enrollment.objects.create(
            user=self.autre_apprenant,
            formation=self.formation_gratuite,
            status='active',
        )

        client = get_auth_client(self.apprenant)
        url = reverse('enrollments:enrollment-detail', kwargs={'pk': enrollment.pk})
        response = client.get(url)

        # 404 car ce n'est pas dans son queryset
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ─────────────────────────────────────────────────────────────────────────────
# TESTS WEBHOOK ET CONFIRMATION/ANNULATION
# ─────────────────────────────────────────────────────────────────────────────

class WebhookAPITest(TestCase):
    """Teste l'endpoint webhook /api/enrollments/webhook/."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='form4@test.com', password='pass', role=User.Role.FORMATEUR
        )
        self.apprenant = User.objects.create_user(
            email='app4@test.com', password='pass', role=User.Role.APPRENANT
        )
        self.formation = create_formation(self.formateur, prix=5000)

    def test_webhook_succes_active_inscription(self):
        """
        Un webhook 'success' de l'opérateur doit activer l'inscription.
        Simule la vraie notification que l'opérateur envoie à notre serveur.
        """
        # Créer une inscription en attente
        enrollment = EnrollmentService.enroll(
            self.apprenant, self.formation.pk,
            phone_number='+237655000000', provider='orange_money'
        )

        client = APIClient()  # Pas d'auth JWT (endpoint public)
        url = reverse('enrollments:payment-webhook')

        response = client.post(url, {
            'enrollment_id': enrollment.pk,
            'transaction_id': 'ORANGE_REAL_TXN_789',
            'status': 'success',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Vérifier que l'inscription est maintenant active
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, Enrollment.Status.ACTIVE)

    def test_webhook_echec_annule_inscription(self):
        """Un webhook 'failed' doit annuler l'inscription."""
        enrollment = EnrollmentService.enroll(
            self.apprenant, self.formation.pk,
            phone_number='+237655000000', provider='mtn_momo'
        )

        client = APIClient()
        url = reverse('enrollments:payment-webhook')

        response = client.post(url, {
            'enrollment_id': enrollment.pk,
            'transaction_id': 'MTN_FAILED_TXN',
            'status': 'failed',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, Enrollment.Status.CANCELLED)


class ConfirmCancelAPITest(TestCase):
    """Teste la confirmation manuelle et l'annulation via API."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='form5@test.com', password='pass', role=User.Role.FORMATEUR
        )
        self.apprenant = User.objects.create_user(
            email='app5@test.com', password='pass', role=User.Role.APPRENANT
        )
        self.admin = User.objects.create_user(
            email='admin5@test.com', password='pass',
            role=User.Role.FORMATEUR, is_also_admin=True
        )
        self.formation = create_formation(self.formateur, prix=5000)

    def test_admin_peut_confirmer_manuellement(self):
        """POST /enrollments/<id>/confirm/ → admin peut activer une inscription."""
        enrollment = EnrollmentService.enroll(
            self.apprenant, self.formation.pk,
            phone_number='+237655000000', provider='orange_money'
        )

        client = get_auth_client(self.admin)
        url = reverse('enrollments:enrollment-confirm', kwargs={'enrollment_id': enrollment.pk})
        response = client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, Enrollment.Status.ACTIVE)

    def test_apprenant_ne_peut_pas_confirmer(self):
        """Un apprenant ne peut pas confirmer lui-même son paiement (403)."""
        enrollment = EnrollmentService.enroll(
            self.apprenant, self.formation.pk,
            phone_number='+237655000000', provider='orange_money'
        )

        client = get_auth_client(self.apprenant)
        url = reverse('enrollments:enrollment-confirm', kwargs={'enrollment_id': enrollment.pk})
        response = client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_apprenant_peut_annuler_sa_propre_inscription(self):
        """POST /enrollments/<id>/cancel/ → l'apprenant peut annuler sa propre inscription."""
        enrollment = EnrollmentService.enroll(
            self.apprenant, self.formation.pk,
            phone_number='+237655000000', provider='orange_money'
        )

        client = get_auth_client(self.apprenant)
        url = reverse('enrollments:enrollment-cancel', kwargs={'enrollment_id': enrollment.pk})
        response = client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, Enrollment.Status.CANCELLED)

    def test_apprenant_ne_peut_pas_annuler_inscription_dautrui(self):
        """Un apprenant ne peut pas annuler l'inscription d'un autre (403)."""
        autre_apprenant = User.objects.create_user(
            email='autre5@test.com', password='pass', role=User.Role.APPRENANT
        )
        formation2 = create_formation(self.formateur, titre='Formation Autre', prix=0)
        enrollment = Enrollment.objects.create(
            user=autre_apprenant, formation=formation2, status='pending'
        )

        client = get_auth_client(self.apprenant)
        url = reverse('enrollments:enrollment-cancel', kwargs={'enrollment_id': enrollment.pk})
        response = client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
