"""
Services pour l'app 'progress'.

Contient la logique métier du suivi de progression.
"""

from decimal import Decimal

from django.utils import timezone

from .models import FormationProgress, LessonProgress


class ProgressService:
    """Opérations métier sur la progression des apprenants."""

    @staticmethod
    def mark_lesson_complete(user, lesson_id):
        """
        Marque une leçon comme terminée et recalcule la progression.

        Args:
            user: l'apprenant
            lesson_id: ID de la leçon

        Returns:
            LessonProgress: la progression de la leçon mise à jour
        """
        from apps.courses.models import Lesson

        try:
            lesson = Lesson.objects.select_related('module__formation').get(pk=lesson_id)
        except Lesson.DoesNotExist:
            raise ValueError("Leçon introuvable.")

        # Obtenir ou créer la progression de la leçon
        lesson_progress, created = LessonProgress.objects.get_or_create(
            user=user,
            lesson=lesson,
        )
        lesson_progress.completed = True
        lesson_progress.save()

        # Mettre à jour la dernière leçon accédée
        ProgressService.update_last_accessed(user, lesson_id)

        # Recalculer la progression globale de la formation
        ProgressService.recalculate_formation_progress(user, lesson.module.formation)

        return lesson_progress

    @staticmethod
    def save_video_position(user, lesson_id, position_seconds):
        """
        Sauvegarde la position dans une vidéo.

        Args:
            user: l'apprenant
            lesson_id: ID de la leçon
            position_seconds: position en secondes

        Returns:
            LessonProgress: la progression mise à jour
        """
        from apps.courses.models import Lesson

        try:
            lesson = Lesson.objects.select_related('module__formation').get(pk=lesson_id)
        except Lesson.DoesNotExist:
            raise ValueError("Leçon introuvable.")

        lesson_progress, created = LessonProgress.objects.get_or_create(
            user=user,
            lesson=lesson,
        )
        lesson_progress.video_position_seconds = position_seconds
        lesson_progress.last_accessed_at = timezone.now()
        lesson_progress.save()

        # Mettre à jour la dernière leçon accédée
        ProgressService.update_last_accessed(user, lesson_id)

        return lesson_progress

    @staticmethod
    def get_or_create_lesson_progress(user, lesson):
        """
        Retourne ou crée la progression d'une leçon et marque l'accès.

        Args:
            user: l'apprenant
            lesson: instance de Lesson

        Returns:
            LessonProgress
        """
        lesson_progress, created = LessonProgress.objects.get_or_create(
            user=user,
            lesson=lesson,
        )
        if not created:
            lesson_progress.last_accessed_at = timezone.now()
            lesson_progress.save()
        return lesson_progress

    @staticmethod
    def update_last_accessed(user, lesson_id):
        """
        Met à jour la dernière leçon accédée dans la progression de la formation.

        Args:
            user: l'apprenant
            lesson_id: ID de la leçon
        """
        from apps.courses.models import Lesson

        lesson = Lesson.objects.select_related('module__formation').get(pk=lesson_id)
        formation = lesson.module.formation

        progress, _ = FormationProgress.objects.get_or_create(
            user=user,
            formation=formation,
        )
        progress.last_accessed_lesson = lesson
        progress.last_accessed_at = timezone.now()
        progress.save()

    @staticmethod
    def recalculate_formation_progress(user, formation):
        """
        Recalcule la progression globale d'un apprenant dans une formation.

        Formule :
            percentage = (completed_lessons + passed_quizzes) / (total_lessons + total_quizzes) × 100

        Args:
            user: l'apprenant
            formation: la formation
        """
        from apps.courses.models import Lesson

        # Compter les leçons totales
        total_lessons = Lesson.objects.filter(module__formation=formation).count()

        # Compter les leçons terminées
        completed_lessons = LessonProgress.objects.filter(
            user=user,
            lesson__module__formation=formation,
            completed=True,
        ).count()

        # Compter les quiz totaux et validés (via QuizAttempt)
        total_quizzes = 0
        passed_quizzes = 0

        for module in formation.modules.all():
            if hasattr(module, 'quiz'):
                total_quizzes += 1
                # Vérifier si l'apprenant a validé ce quiz
                latest_attempt = module.quiz.attempts.filter(
                    user=user,
                    passed=True,
                ).first()
                if latest_attempt:
                    passed_quizzes += 1

        # Calculer le pourcentage
        total_items = total_lessons + total_quizzes
        if total_items == 0:
            percentage = Decimal('0.00')
        else:
            percentage = Decimal(str((completed_lessons + passed_quizzes) / total_items * 100)).quantize(
                Decimal('0.01')
            )

        # Mettre à jour la progression
        progress, _ = FormationProgress.objects.get_or_create(
            user=user,
            formation=formation,
        )
        progress.completed_lessons = completed_lessons
        progress.total_lessons = total_lessons
        progress.passed_quizzes = passed_quizzes
        progress.total_quizzes = total_quizzes
        progress.percentage = percentage
        progress.is_completed = (percentage >= Decimal('100.00'))
        progress.save()

        return progress
