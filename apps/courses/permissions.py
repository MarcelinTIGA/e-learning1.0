"""
Permissions personnalisées pour l'app 'courses'.

IsFormateurOwnerOrAdmin   : seul le formateur propriétaire ou un admin peut modifier/supprimer
IsPublishedOrOwnerOrAdmin : formation publiée OU formateur propriétaire OU admin
"""

from rest_framework import permissions


class IsFormateurOwnerOrAdmin(permissions.BasePermission):
    """
    Permission au niveau objet.
    Autorise l'accès si :
      - L'utilisateur est administrateur, OU
      - L'utilisateur est le formateur propriétaire de la formation/module/leçon
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_administrateur:
            return True

        # Déterminer le formateur selon le type d'objet
        if hasattr(obj, 'formateur'):
            # Formation directe
            return obj.formateur == user
        if hasattr(obj, 'formation'):
            # Module (a un attribut formation direct)
            return obj.formation.formateur == user
        if hasattr(obj, 'module'):
            # Lesson (passe par module → formation)
            return obj.module.formation.formateur == user

        return False


class IsPublishedOrOwnerOrAdmin(permissions.BasePermission):
    """
    Permission au niveau objet.
    Autorise l'accès si :
      - La formation est publiée (visible par tous), OU
      - L'utilisateur est le formateur propriétaire, OU
      - L'utilisateur est administrateur
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Formation publiée = visible par tous
        if getattr(obj, 'is_published', False):
            return True

        # Admin ou propriétaire
        if user.is_administrateur:
            return True

        if hasattr(obj, 'formateur'):
            return obj.formateur == user

        return False
