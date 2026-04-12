"""
Serializers pour l'app 'enrollments'.

Rôle des serializers :
    - Convertir les objets Python (Enrollment, Payment) en JSON pour l'API
    - Valider les données envoyées par le client avant de les traiter
    - Contrôler quels champs sont exposés (ex: cacher les données sensibles)

Serializers disponibles :
    - EnrollmentSerializer      : inscription (lecture, avec infos formation)
    - EnrollmentCreateSerializer: données pour créer une inscription (écriture)
    - PaymentSerializer         : paiement (lecture)
    - PaymentWebhookSerializer  : données du webhook opérateur (entrée externe)
"""

from rest_framework import serializers

from .models import Enrollment, Payment


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer de lecture pour un paiement.

    Exposé à l'apprenant pour qu'il puisse voir le statut de son paiement.
    On ne montre PAS le transaction_id (trop technique, potentiellement sensible).
    """

    class Meta:
        model = Payment
        fields = (
            'id',
            'provider',         # 'orange_money' ou 'mtn_momo'
            'phone_number',     # Numéro qui a payé
            'amount',           # Montant en XAF
            'currency',         # Toujours 'XAF'
            'status',           # 'pending', 'success', 'failed'
            'initiated_at',     # Quand le paiement a été initié
        )
        # transaction_id exclu : donnée interne, pas utile pour l'apprenant


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializer de lecture pour une inscription.

    Inclut les informations essentielles sur la formation et le paiement.
    Utilisé dans les réponses API (GET /enrollments/, GET /enrollments/<id>/).
    """

    # Afficher le titre de la formation plutôt que son ID (plus lisible)
    formation_titre = serializers.SerializerMethodField()

    # Afficher l'email de l'apprenant (utile pour les admins)
    user_email = serializers.SerializerMethodField()

    # Inclure les détails du paiement si disponible
    # many=False : il y a au plus 1 paiement par inscription (OneToOneField)
    # read_only=True : on ne modifie pas le paiement via ce serializer
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = (
            'id',
            'user_email',       # Calculé dynamiquement
            'formation_titre',  # Calculé dynamiquement
            'status',           # 'pending', 'active', 'completed', 'cancelled'
            'enrolled_at',      # Date d'inscription
            'updated_at',       # Dernière mise à jour
            'payment',          # Détails du paiement (None pour formations gratuites)
        )

    def get_formation_titre(self, obj):
        """Retourne le titre de la formation associée à cette inscription."""
        return obj.formation.titre

    def get_user_email(self, obj):
        """Retourne l'email de l'apprenant."""
        return obj.user.email


class EnrollmentCreateSerializer(serializers.Serializer):
    """
    Serializer pour créer une nouvelle inscription.

    Données attendues dans le corps de la requête POST :
        {
            "formation_id": 5,
            "phone_number": "+237655000000",   // Requis pour formations payantes
            "provider": "orange_money"          // 'orange_money' ou 'mtn_momo'
        }

    Pour une formation GRATUITE, seul formation_id est nécessaire.
    Pour une formation PAYANTE, phone_number et provider sont obligatoires.
    """

    # ID de la formation à laquelle l'apprenant veut s'inscrire
    formation_id = serializers.IntegerField()

    # Numéro de téléphone pour le paiement Mobile Money
    # required=False car non nécessaire pour les formations gratuites
    phone_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        default='',
    )

    # Opérateur de paiement choisi
    # required=False pour la même raison
    provider = serializers.ChoiceField(
        choices=Payment.Provider.choices,   # 'orange_money' ou 'mtn_momo'
        required=False,
        allow_blank=True,
        default='',
    )


class PaymentWebhookSerializer(serializers.Serializer):
    """
    Serializer pour les callbacks des opérateurs de paiement.

    Quand Orange Money ou MTN confirme un paiement, ils envoient une requête
    HTTP à notre serveur (webhook). Ce serializer valide ces données entrantes.

    Format attendu (commun aux deux opérateurs) :
        {
            "enrollment_id": 42,
            "transaction_id": "ORANGE_TXN_12345",
            "status": "success"
        }

    Note : Dans la réalité, chaque opérateur a son propre format de webhook.
           Cette structure est simplifiée pour l'environnement de développement.
    """

    enrollment_id  = serializers.IntegerField()
    transaction_id = serializers.CharField(max_length=100)

    # Statuts possibles envoyés par l'opérateur
    status = serializers.ChoiceField(
        choices=['success', 'failed'],  # L'opérateur dit succès ou échec
    )
