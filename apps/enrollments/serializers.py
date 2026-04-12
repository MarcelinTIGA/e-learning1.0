"""
Serializers pour l'app 'enrollments'.

  - EnrollmentSerializer         : lecture d'une inscription
  - EnrollmentCreateSerializer   : création d'une inscription
  - PaymentSerializer            : lecture d'un paiement
  - PaymentWebhookSerializer     : validation du webhook de paiement
"""

from rest_framework import serializers

from .models import Enrollment, Payment


class EnrollmentSerializer(serializers.ModelSerializer):
    """Lecture d'une inscription."""

    formation_titre = serializers.SerializerMethodField()
    formation_image = serializers.SerializerMethodField()
    is_paid = serializers.BooleanField(read_only=True)
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            'id', 'user', 'formation', 'formation_titre', 'formation_image',
            'status', 'is_paid', 'payment_status', 'enrolled_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'enrolled_at', 'updated_at']

    def get_formation_titre(self, obj):
        return obj.formation.titre if obj.formation else None

    def get_formation_image(self, obj):
        if obj.formation and obj.formation.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.formation.image.url)
            return obj.formation.image.url
        return None

    def get_payment_status(self, obj):
        if hasattr(obj, 'payment'):
            return obj.payment.status
        return None


class EnrollmentCreateSerializer(serializers.Serializer):
    """Création d'une inscription."""

    formation_id = serializers.IntegerField(required=True)
    phone_number = serializers.CharField(max_length=20, required=False, default='')
    provider = serializers.ChoiceField(
        choices=Payment.Provider.choices,
        required=False,
    )

    def validate_formation_id(self, value):
        from apps.courses.models import Formation
        try:
            formation = Formation.objects.get(pk=value)
        except Formation.DoesNotExist:
            raise serializers.ValidationError("Formation introuvable.")
        if not formation.is_published:
            raise serializers.ValidationError("Cette formation n'est pas publiée.")
        return value

    def validate(self, attrs):
        formation_id = attrs.get('formation_id')
        from apps.courses.models import Formation
        formation = Formation.objects.get(pk=formation_id)

        # Si formation payante → phone_number et provider requis
        if not formation.is_free:
            if not attrs.get('phone_number'):
                raise serializers.ValidationError(
                    {"phone_number": "Le numéro de téléphone est requis pour les formations payantes."}
                )
            if not attrs.get('provider'):
                raise serializers.ValidationError(
                    {"provider": "L'opérateur de paiement est requis pour les formations payantes."}
                )

        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    """Lecture d'un paiement."""

    class Meta:
        model = Payment
        fields = [
            'id', 'enrollment', 'amount', 'currency', 'provider',
            'phone_number', 'transaction_id', 'status',
            'initiated_at', 'updated_at',
        ]
        read_only_fields = ['id', 'initiated_at', 'updated_at']


class PaymentWebhookSerializer(serializers.Serializer):
    """Validation des données envoyées par l'opérateur de paiement (webhook)."""

    enrollment_id = serializers.IntegerField(required=True)
    transaction_id = serializers.CharField(max_length=100, required=True)
    status = serializers.ChoiceField(
        choices=['success', 'failed'],
        required=True,
    )
    provider = serializers.ChoiceField(
        choices=Payment.Provider.choices,
        required=False,
        default=Payment.Provider.ORANGE,
    )
