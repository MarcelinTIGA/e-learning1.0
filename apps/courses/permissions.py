"""
Permissions spécifiques à l'app 'courses'.

Ces permissions s'ajoutent aux permissions globales définies dans apps/users/permissions.py.
Elles gèrent les règles d'accès aux ressources de cours selon le rôle et la propriété.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsFormateurOwnerOrAdmin(BasePermission):
    """
    Permission au niveau de l'OBJET (has_object_permission).

    Règle :
        - Les administrateurs ont toujours accès (lecture + écriture).
        - Le formateur propriétaire de la formation peut modifier.
        - Les autres utilisateurs ne peuvent PAS modifier.

    Utilisée pour les endpoints de modification des formations/modules/leçons.
    """

    def has_object_permission(self, request, view, obj):
        # SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS') — méthodes qui ne modifient pas les données
        # Pour les lectures, on laisse passer (la restriction d'accès est gérée ailleurs)
        if request.method in SAFE_METHODS:
            return True

        # Les administrateurs peuvent tout modifier
        if request.user.is_administrateur:
            return True

        # Récupère le formateur propriétaire selon le type d'objet
        # Une Formation a un champ 'formateur' direct
        # Un Module ou une Leçon nécessite de remonter à la Formation parente
        if hasattr(obj, 'formateur'):
            # Cas : objet Formation
            return obj.formateur == request.user
        elif hasattr(obj, 'formation'):
            # Cas : objet Module (obj.formation.formateur)
            return obj.formation.formateur == request.user
        elif hasattr(obj, 'module'):
            # Cas : objet Lesson (obj.module.formation.formateur)
            return obj.module.formation.formateur == request.user

        return False


class IsPublishedOrOwnerOrAdmin(BasePermission):
    """
    Permission pour l'accès en LECTURE aux formations.

    Règle :
        - Une formation publiée (is_published=True) est accessible à tous.
        - Une formation non publiée n'est visible que par son formateur ou un admin.

    Utilisée pour les endpoints du catalogue public.
    """

    def has_object_permission(self, request, view, obj):
        # Une formation publiée est accessible à tout le monde
        if obj.is_published:
            return True

        # Si non publiée : seul le formateur propriétaire ou un admin peut voir
        if request.user.is_authenticated:
            if request.user.is_administrateur:
                return True
            if hasattr(obj, 'formateur') and obj.formateur == request.user:
                return True

        return False
