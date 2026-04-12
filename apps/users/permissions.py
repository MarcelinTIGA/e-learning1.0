from rest_framework.permissions import BasePermission


class IsApprenant(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_apprenant


class IsFormateur(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_formateur


class IsAdministrateur(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_administrateur


class IsFormateurOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_formateur or request.user.is_administrateur
        )


class IsOwnerOrAdmin(BasePermission):
    """Permission au niveau objet : l'utilisateur est le propriétaire ou un admin."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_administrateur:
            return True
        owner_field = getattr(view, 'owner_field', 'user')
        return getattr(obj, owner_field) == request.user
