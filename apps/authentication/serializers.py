"""
Serializers pour l'app 'authentication'.

  - RegisterSerializer         : inscription
  - LoginSerializer            : connexion
  - ChangePasswordSerializer   : changement mot de passe
  - PasswordResetRequestSerializer  : demande de réinitialisation
  - PasswordResetConfirmSerializer  : confirmation de réinitialisation
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.users.models import User


class RegisterSerializer(serializers.ModelSerializer):
    """Inscription d'un nouvel utilisateur."""

    password1 = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'role', 'password1', 'password2']

    def validate(self, attrs):
        if attrs['password1'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "Les mots de passe ne correspondent pas."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password1')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Connexion par email + mot de passe."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(request=self.context.get('request'), email=email, password=password)

        if not user:
            raise serializers.ValidationError("Email ou mot de passe incorrect.")

        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé.")

        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Changement de mot de passe (utilisateur authentifié)."""

    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        request = self.context.get('request')

        if not request.user.check_password(attrs['old_password']):
            raise serializers.ValidationError({"old_password": "Ancien mot de passe incorrect."})

        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Les mots de passe ne correspondent pas."})

        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Demande de réinitialisation de mot de passe."""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        try:
            self.user = User.objects.get(email=value)
        except User.DoesNotExist:
            self.user = None
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Confirmation de réinitialisation de mot de passe."""

    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
