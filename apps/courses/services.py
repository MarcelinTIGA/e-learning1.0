"""
Services pour l'app 'courses'.

Contient la logique métier qui ne devrait pas être dans les views.
"""

from .models import Formation, Module, Lesson


class CourseService:
    """Opérations métier sur les formations, modules et leçons."""

    @staticmethod
    def get_user_formations(user):
        """Retourne les formations visibles par l'utilisateur."""
        if user.is_administrateur:
            return Formation.objects.all()
        if user.is_formateur:
            return Formation.objects.filter(formateur=user)
        # Apprenant : formations publiées uniquement
        return Formation.objects.filter(is_published=True)

    @staticmethod
    def get_formation_detail(formation, user=None):
        """Retourne une formation avec ses modules et leçons préchargés."""
        return (
            Formation.objects
            .select_related('formateur', 'categorie')
            .prefetch_related('modules__lessons')
            .get(pk=formation.pk)
        )

    @staticmethod
    def calculate_duration_minutes(formation):
        """Calcule la durée totale d'une formation en minutes (somme des leçons)."""
        total = 0
        for module in formation.modules.all():
            for lesson in module.lessons.all():
                total += lesson.duration_minutes
        return total
