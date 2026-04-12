"""
Serializers pour l'app 'certificates'.

  - CertificateSerializer        : lecture d'un certificat
  - CertificateCreateSerializer  : création manuelle (admin/formateur)
  - CertificateVerifySerializer  : réponse de vérification
"""

from rest_framework import serializers

from .models import Certificate


class CertificateSerializer(serializers.ModelSerializer):
    """Lecture d'un certificat."""

    user_email = serializers.SerializerMethodField()
    formation_titre = serializers.CharField(source='formation_titre_snapshot')
    formation_duration_minutes = serializers.IntegerField(
        source='formation_duration_snapshot',
    )

    class Meta:
        model = Certificate
        fields = [
            'id', 'user', 'user_email', 'formation', 'formation_titre',
            'formation_duration_minutes', 'verification_code',
            'pdf_file', 'issued_at',
        ]
        read_only_fields = ['id', 'verification_code', 'issued_at']

    def get_user_email(self, obj):
        return obj.user.email if obj.user else None


class CertificateCreateSerializer(serializers.Serializer):
    """
    Création manuelle d'un certificat (réservé aux admins).

    AMBIGUÏTÉ : Pourquoi permettre la création manuelle ?
      - Cas de support : un apprenant a terminé mais le signal n'a pas fonctionné
      - Import de données : migration depuis un ancien système
      - Délivrance rétroactive : former des employés avant la mise en place de la plateforme
    """

    user_id = serializers.UUIDField(required=True)
    formation_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        from apps.courses.models import Formation
        from apps.users.models import User

        try:
            self.user = User.objects.get(pk=attrs['user_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError({"user_id": "Utilisateur introuvable."})

        try:
            self.formation = Formation.objects.get(pk=attrs['formation_id'])
        except Formation.DoesNotExist:
            raise serializers.ValidationError({"formation_id": "Formation introuvable."})

        # Vérifier qu'un certificat n'existe pas déjà
        if Certificate.objects.filter(user=self.user, formation=self.formation).exists():
            raise serializers.ValidationError(
                "Un certificat existe déjà pour cet utilisateur et cette formation."
            )

        return attrs


class CertificateVerifySerializer(serializers.Serializer):
    """
    Réponse de vérification d'un certificat.

    Retourné quand un employeur ou un tiers vérifie un code.
    Pas de données sensibles : seulement les infos publiques du certificat.
    """

    is_valid = serializers.BooleanField()
    message = serializers.CharField()
    certificate = serializers.SerializerMethodField()

    def get_certificate(self, obj):
        """
        Ne retourne les détails que si le certificat est valide.
        AMBIGUÏTÉ : Pourquoi ne pas tout retourner même si invalide ?
          - Retourner des infos sur un code invalide pourrait permettre
            de "deviner" des codes valides par brute force.
          - En cas d'invalidité, on retourne uniquement le message d'erreur.
        """
        if not obj.get('is_valid'):
            return None
        cert = obj.get('certificate')
        if not cert:
            return None
        return {
            'verification_code': cert.verification_code,
            'issued_to': cert.user.full_name,
            'formation': cert.formation_titre_snapshot,
            'duration_minutes': cert.formation_duration_snapshot,
            'issued_at': cert.issued_at,
        }
