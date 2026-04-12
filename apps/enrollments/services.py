"""
Services pour l'app 'enrollments'.

Contient la logique métier des inscriptions et paiements.
"""

from django.utils import timezone

from .models import Enrollment, Payment


class EnrollmentService:
    """Opérations métier sur les inscriptions et paiements."""

    @staticmethod
    def enroll(user, formation_id, phone_number='', provider=''):
        """
        Inscrit un utilisateur à une formation.

        Si la formation est gratuite → inscription directe (ACTIVE).
        Si la formation est payante → inscription en attente (PENDING) + création d'un Payment.

        Args:
            user: l'utilisateur qui s'inscrit
            formation_id: ID de la formation
            phone_number: numéro de téléphone (si payante)
            provider: opérateur de paiement (si payante)

        Returns:
            Enrollment: l'inscription créée

        Raises:
            ValueError: si l'utilisateur est déjà inscrit ou si la formation est introuvable
        """
        from apps.courses.models import Formation

        try:
            formation = Formation.objects.get(pk=formation_id)
        except Formation.DoesNotExist:
            raise ValueError("Formation introuvable.")

        # Vérifier que l'utilisateur n'est pas déjà inscrit
        if Enrollment.objects.filter(user=user, formation=formation).exists():
            raise ValueError("Vous êtes déjà inscrit à cette formation.")

        # Formations gratuites : accès direct
        if formation.is_free:
            enrollment = Enrollment.objects.create(
                user=user,
                formation=formation,
                status=Enrollment.Status.ACTIVE,
            )
            return enrollment

        # Formations payantes : vérification des paramètres
        if not phone_number or not provider:
            raise ValueError("Le numéro de téléphone et l'opérateur sont requis pour les formations payantes.")

        # Créer l'inscription en attente
        enrollment = Enrollment.objects.create(
            user=user,
            formation=formation,
            status=Enrollment.Status.PENDING,
        )

        # Créer le paiement associé
        Payment.objects.create(
            enrollment=enrollment,
            amount=formation.prix,
            currency='XAF',
            provider=provider,
            phone_number=phone_number,
            status=Payment.Status.PENDING,
        )

        return enrollment

    @staticmethod
    def confirm_payment(enrollment_id):
        """
        Confirme le paiement d'une inscription et active l'accès.

        Args:
            enrollment_id: ID de l'inscription

        Returns:
            Enrollment: l'inscription mise à jour

        Raises:
            ValueError: si le paiement est déjà confirmé ou l'inscription introuvable
        """
        try:
            enrollment = Enrollment.objects.select_related('payment').get(pk=enrollment_id)
        except Enrollment.DoesNotExist:
            raise ValueError("Inscription introuvable.")

        if enrollment.status == Enrollment.Status.ACTIVE:
            raise ValueError("Cette inscription est déjà active.")

        if enrollment.status == Enrollment.Status.COMPLETED:
            raise ValueError("Cette inscription est déjà terminée.")

        # Mettre à jour le paiement si existant
        if hasattr(enrollment, 'payment'):
            enrollment.payment.status = Payment.Status.SUCCESS
            enrollment.payment.save()

        # Activer l'inscription
        enrollment.status = Enrollment.Status.ACTIVE
        enrollment.save()

        return enrollment

    @staticmethod
    def cancel_enrollment(enrollment_id):
        """
        Annule une inscription.

        Args:
            enrollment_id: ID de l'inscription

        Returns:
            Enrollment: l'inscription annulée

        Raises:
            ValueError: si l'inscription ne peut pas être annulée
        """
        try:
            enrollment = Enrollment.objects.select_related('payment').get(pk=enrollment_id)
        except Enrollment.DoesNotExist:
            raise ValueError("Inscription introuvable.")

        if enrollment.status == Enrollment.Status.COMPLETED:
            raise ValueError("Impossible d'annuler une inscription terminée.")

        # Annuler le paiement si existant
        if hasattr(enrollment, 'payment') and enrollment.payment.status == Payment.Status.PENDING:
            enrollment.payment.status = Payment.Status.FAILED
            enrollment.payment.save()

        enrollment.status = Enrollment.Status.CANCELLED
        enrollment.save()

        return enrollment
