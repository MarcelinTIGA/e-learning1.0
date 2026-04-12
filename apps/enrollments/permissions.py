"""
Permissions personnalisées pour l'app 'enrollments'.

IsEnrolledAndPaid est une permission CROSS-APP :
    Elle est utilisée par apps.courses, apps.quizzes, et apps.progress
    pour vérifier qu'un apprenant a payé et a accès au contenu.

Comment DRF gère les permissions :
    1. Chaque view a une liste `permission_classes`
    2. DRF appelle has_permission(request, view) d'abord
    3. Si l'objet est nécessaire, il appelle has_object_permission(request, view, obj)
    4. Si l'une retourne False → 403 Forbidden (ou 401 si non authentifié)
"""

from rest_framework import permissions

from .models import Enrollment


class IsEnrolledAndPaid(permissions.BasePermission):
    """
    Vérifie qu'un apprenant est inscrit ET a payé pour une formation.

    Cette permission est utilisée pour protéger l'accès aux ressources
    d'une formation (modules, leçons, quiz).

    Usage dans une view :
        permission_classes = [IsAuthenticated, IsEnrolledAndPaid]

    La view doit fournir formation_id via :
        - URL kwargs : self.kwargs.get('formation_id') ou 'formation_pk'
        - L'objet : obj.formation_id ou obj.module.formation_id

    Note : Les formateurs et admins ont toujours accès (ils n'ont pas besoin
           de s'inscrire à leur propre formation).
    """

    message = "Vous devez être inscrit et avoir payé pour accéder à ce contenu."

    def has_permission(self, request, view):
        """
        Vérifie l'accès au niveau de la vue (avant de récupérer l'objet).

        Utilisé quand formation_id est dans l'URL (ex: /courses/5/modules/).
        """
        # L'utilisateur doit être authentifié
        if not request.user or not request.user.is_authenticated:
            return False

        # Les formateurs et admins passent toujours
        if request.user.is_formateur or request.user.is_administrateur:
            return True

        # Chercher formation_id dans les URL kwargs
        # Les views peuvent nommer le paramètre différemment
        formation_id = (
            view.kwargs.get('formation_id')
            or view.kwargs.get('formation_pk')
        )

        if not formation_id:
            # Pas de formation_id dans l'URL → on laisse passer
            # has_object_permission vérifiera au niveau de l'objet
            return True

        return self._check_enrollment(request.user, formation_id)

    def has_object_permission(self, request, view, obj):
        """
        Vérifie l'accès au niveau de l'objet (après récupération depuis la DB).

        Utilisé quand on accède à un objet spécifique (ex: GET /lessons/42/).
        On remonte la hiérarchie pour trouver la formation associée.
        """
        # Les formateurs et admins passent toujours
        if request.user.is_formateur or request.user.is_administrateur:
            return True

        # Remonter la hiérarchie pour trouver formation_id
        # Selon le type d'objet : Lesson → Module → Formation
        #                         Module → Formation
        #                         Formation directement
        formation_id = self._extract_formation_id(obj)

        if formation_id is None:
            # Impossible de déterminer la formation → on refuse par sécurité
            return False

        return self._check_enrollment(request.user, formation_id)

    @staticmethod
    def _extract_formation_id(obj):
        """
        Extrait l'ID de formation depuis différents types d'objets.

        Supporte Formation, Module, Lesson (et tout objet avec .formation_id
        ou .module.formation_id).
        """
        # L'objet est directement une Formation
        if hasattr(obj, 'is_published'):
            return obj.pk

        # L'objet a un lien direct vers Formation (ex: Module)
        if hasattr(obj, 'formation_id'):
            return obj.formation_id

        # L'objet est lié via Module (ex: Lesson, Quiz)
        if hasattr(obj, 'module') and hasattr(obj.module, 'formation_id'):
            return obj.module.formation_id

        return None

    @staticmethod
    def _check_enrollment(user, formation_id) -> bool:
        """
        Vérifie dans la base de données si l'apprenant est inscrit et a payé.

        Returns:
            True si l'inscription existe et est active (ou complétée)
            False sinon
        """
        return Enrollment.objects.filter(
            user=user,
            formation_id=formation_id,
            # ACTIVE = paiement validé, COMPLETED = formation terminée (toujours accès)
            status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED],
        ).exists()
