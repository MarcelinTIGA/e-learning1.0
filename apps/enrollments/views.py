"""
Views pour l'app 'enrollments'.

Endpoints disponibles :
    POST   /api/enrollments/                    — S'inscrire à une formation
    GET    /api/enrollments/                    — Mes inscriptions (apprenant) / toutes (admin)
    GET    /api/enrollments/<id>/               — Détail d'une inscription
    GET    /api/enrollments/<enrollment_id>/payment/   — Statut du paiement
    POST   /api/enrollments/<enrollment_id>/confirm/   — Confirmer manuellement (admin)
    POST   /api/enrollments/<enrollment_id>/cancel/    — Annuler une inscription
    POST   /api/enrollments/webhook/            — Callback de l'opérateur (webhook)

Séparation des responsabilités :
    - Views : reçoivent la requête HTTP, délèguent au service, retournent la réponse
    - Services : contiennent TOUTE la logique métier (voir services.py)
    - Serializers : valident les données et formatent les réponses (voir serializers.py)
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsFormateurOrAdmin

from .models import Enrollment, Payment
from .serializers import (
    EnrollmentCreateSerializer,
    EnrollmentSerializer,
    PaymentSerializer,
    PaymentWebhookSerializer,
)
from .services import EnrollmentService


class EnrollmentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/enrollments/  — Lister mes inscriptions
    POST /api/enrollments/  — S'inscrire à une formation

    GET :
        - Apprenant : voit uniquement SES inscriptions
        - Admin     : voit TOUTES les inscriptions

    POST :
        Corps JSON attendu :
            {
                "formation_id": 5,
                "phone_number": "+237655000000",  // Si formation payante
                "provider": "orange_money"         // Si formation payante
            }
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Retourne un serializer différent selon GET (lecture) ou POST (création)."""
        if self.request.method == 'POST':
            return EnrollmentCreateSerializer
        return EnrollmentSerializer

    def get_queryset(self):
        """
        Filtre les inscriptions selon le rôle de l'utilisateur connecté.
        select_related : charge formation et user en 1 requête SQL (pas N+1).
        prefetch_related : charge les paiements associés en 1 requête supplémentaire.
        """
        user = self.request.user

        if user.is_administrateur:
            # Admin : voit tout (utile pour la gestion/support)
            return Enrollment.objects.select_related(
                'user', 'formation'
            ).prefetch_related('payment').all()

        # Apprenant (ou formateur consultant ses propres inscriptions)
        return Enrollment.objects.select_related(
            'user', 'formation'
        ).prefetch_related('payment').filter(user=user)

    def create(self, request, *args, **kwargs):
        """
        Crée une nouvelle inscription.

        Override de create() pour déléguer au service métier
        plutôt qu'au serializer directement (qui ne sait pas créer une Enrollment).
        """
        # 1. Valider les données entrantes
        serializer = EnrollmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 2. Déléguer la logique au service
        try:
            enrollment = EnrollmentService.enroll(
                user=request.user,
                formation_id=data['formation_id'],
                phone_number=data.get('phone_number', ''),
                provider=data.get('provider', ''),
            )
        except ValueError as e:
            # ValueError = règle métier violée (ex: déjà inscrit, formation non publiée)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Erreur inattendue (ex: formation introuvable)
            return Response({'detail': str(e)}, status=status.HTTP_404_NOT_FOUND)

        # 3. Retourner l'inscription créée
        result = EnrollmentSerializer(enrollment)
        return Response(result.data, status=status.HTTP_201_CREATED)


class EnrollmentDetailView(generics.RetrieveAPIView):
    """
    GET /api/enrollments/<id>/  — Détail d'une inscription spécifique.

    L'apprenant ne voit que SES inscriptions.
    L'admin voit toutes les inscriptions.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_administrateur:
            return Enrollment.objects.select_related('user', 'formation').prefetch_related('payment').all()
        # L'apprenant ne peut accéder qu'à ses propres inscriptions
        # (get_object retournera 404 si l'ID appartient à quelqu'un d'autre)
        return Enrollment.objects.select_related('user', 'formation').prefetch_related('payment').filter(user=user)


class PaymentDetailView(generics.RetrieveAPIView):
    """
    GET /api/enrollments/<enrollment_id>/payment/
    Voir le statut du paiement pour une inscription donnée.

    Utilisé par l'apprenant pour suivre si son paiement a été confirmé.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_object(self):
        """
        Récupère le Payment associé à l'enrollment_id dans l'URL.
        Vérifie que l'inscription appartient bien à l'utilisateur connecté.
        """
        enrollment_id = self.kwargs.get('enrollment_id')

        # Construire la requête selon le rôle
        enrollment_qs = Enrollment.objects.select_related('payment')
        if not self.request.user.is_administrateur:
            # Sécurité : un apprenant ne peut voir que ses propres paiements
            enrollment_qs = enrollment_qs.filter(user=self.request.user)

        try:
            enrollment = enrollment_qs.get(pk=enrollment_id)
        except Enrollment.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Inscription introuvable.")

        # Vérifier qu'il y a bien un paiement associé
        if not hasattr(enrollment, 'payment'):
            from rest_framework.exceptions import NotFound
            raise NotFound("Aucun paiement associé (formation gratuite ?).")

        return enrollment.payment


class ConfirmPaymentView(APIView):
    """
    POST /api/enrollments/<enrollment_id>/confirm/

    Confirme manuellement une inscription et active l'accès.
    RÉSERVÉ AUX ADMINS.

    Utile pour :
        - Débloquer un apprenant dont le paiement est bloqué
        - Tests et démonstrations
        - Cas de support (le webhook n'a pas été reçu)
    """

    permission_classes = [IsFormateurOrAdmin]

    def post(self, request, enrollment_id):
        try:
            enrollment = EnrollmentService.confirm_payment(enrollment_id)
        except Enrollment.DoesNotExist:
            return Response({'detail': "Inscription introuvable."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(EnrollmentSerializer(enrollment).data)


class CancelEnrollmentView(APIView):
    """
    POST /api/enrollments/<enrollment_id>/cancel/

    Annule une inscription.
    L'apprenant peut annuler sa propre inscription (si encore PENDING).
    L'admin peut annuler n'importe quelle inscription.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, enrollment_id):
        # Vérifier que l'apprenant annule bien SA propre inscription
        try:
            enrollment = Enrollment.objects.get(pk=enrollment_id)
        except Enrollment.DoesNotExist:
            return Response({'detail': "Inscription introuvable."}, status=status.HTTP_404_NOT_FOUND)

        # Seul le propriétaire ou un admin peut annuler
        if not request.user.is_administrateur and enrollment.user != request.user:
            return Response(
                {'detail': "Vous ne pouvez pas annuler cette inscription."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            enrollment = EnrollmentService.cancel_enrollment(enrollment_id)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(EnrollmentSerializer(enrollment).data)


class PaymentWebhookView(APIView):
    """
    POST /api/enrollments/webhook/

    Endpoint appelé par les opérateurs de paiement (Orange Money, MTN)
    pour notifier notre serveur qu'un paiement a été confirmé ou refusé.

    C'est ce qu'on appelle un "webhook" : l'opérateur nous envoie une requête
    HTTP automatiquement quand quelque chose se passe côté paiement.

    SÉCURITÉ IMPORTANTE (TODO pour la production) :
        - Vérifier la signature de la requête (chaque opérateur signe ses webhooks)
        - Whitelist les IPs de l'opérateur
        - Utiliser HTTPS uniquement
        - Loguer toutes les tentatives

    Cet endpoint est intentionnellement PUBLIC (AllowAny) car l'opérateur
    ne peut pas s'authentifier avec un JWT. La sécurité passe par la signature.
    """

    # Pas d'authentification JWT ici : l'opérateur externe n'a pas de token
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Valider le format des données envoyées par l'opérateur
        serializer = PaymentWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        enrollment_id  = data['enrollment_id']
        transaction_id = data['transaction_id']
        webhook_status = data['status']

        # Mettre à jour le transaction_id reçu de l'opérateur
        try:
            payment = Payment.objects.select_related('enrollment').get(
                enrollment_id=enrollment_id
            )
            payment.transaction_id = transaction_id
            payment.save()
        except Payment.DoesNotExist:
            return Response({'detail': "Paiement introuvable."}, status=status.HTTP_404_NOT_FOUND)

        # Traiter selon le statut envoyé par l'opérateur
        try:
            if webhook_status == 'success':
                EnrollmentService.confirm_payment(enrollment_id)
                return Response({'detail': "Paiement confirmé, inscription activée."})
            else:  # 'failed'
                EnrollmentService.cancel_enrollment(enrollment_id)
                return Response({'detail': "Paiement échoué, inscription annulée."})
        except (ValueError, Enrollment.DoesNotExist) as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
