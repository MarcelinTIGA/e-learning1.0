"""
Services métier pour l'app 'progress'.

Ce fichier contient toute la logique de suivi de progression.
Les views et signals appellent ce service — la logique est centralisée ici.

ProgressService fournit :
    - mark_lesson_complete()           : marquer une leçon comme terminée
    - save_video_position()            : sauvegarder la position dans une vidéo
    - update_last_accessed()           : mettre à jour la dernière leçon accédée
    - get_or_create_lesson_progress()  : obtenir/créer un LessonProgress
    - recalculate_formation_progress() : recalculer le pourcentage global

Concept clé — get_or_create :
    Django fournit .get_or_create(field=value) qui fait en une seule requête :
        "Donne-moi l'objet avec ces critères, ou crée-le s'il n'existe pas."
    Retourne (objet, created) où created=True si l'objet vient d'être créé.
    Évite les conditions if/else et les race conditions.
"""

from decimal import Decimal

from django.db import transaction

from apps.courses.models import Formation, Lesson, Module

from .models import FormationProgress, LessonProgress


class ProgressService:
    """Service centralisé pour toutes les opérations de suivi de progression."""

    @staticmethod
    def get_or_create_lesson_progress(user, lesson) -> LessonProgress:
        """
        Obtient ou crée un LessonProgress pour cet apprenant et cette leçon.

        Appelé automatiquement à chaque accès à une leçon, ce qui permet de :
            - Suivre quelle leçon l'apprenant visite (last_accessed_at)
            - Initialiser l'enregistrement de progression au premier accès

        Args:
            user:   L'apprenant
            lesson: La leçon accédée

        Returns:
            Le LessonProgress existant ou nouvellement créé
        """
        # get_or_create : tente d'abord un SELECT, puis un INSERT si absent
        # Le deuxième élément (created) n'est pas utilisé ici mais disponible
        progress, _ = LessonProgress.objects.get_or_create(
            user=user,
            lesson=lesson,
        )
        return progress

    @staticmethod
    @transaction.atomic
    def mark_lesson_complete(user, lesson_id: int) -> LessonProgress:
        """
        Marque une leçon comme terminée et recalcule la progression globale.

        @transaction.atomic : si le recalcul échoue, le marquage est aussi annulé.
        On garantit ainsi que LessonProgress et FormationProgress restent cohérents.

        Args:
            user:      L'apprenant qui termine la leçon
            lesson_id: L'ID de la leçon à marquer

        Returns:
            Le LessonProgress mis à jour

        Raises:
            Lesson.DoesNotExist: Si la leçon n'existe pas
        """
        # select_related : charge le module et la formation en une seule requête SQL
        # au lieu de 3 requêtes séparées (Lesson → Module → Formation)
        lesson = Lesson.objects.select_related('module__formation').get(pk=lesson_id)

        # Obtenir ou créer le suivi de cette leçon
        lesson_progress, _ = LessonProgress.objects.get_or_create(
            user=user,
            lesson=lesson,
        )

        # Marquer comme terminée seulement si pas déjà fait (évite le recalcul inutile)
        if not lesson_progress.completed:
            lesson_progress.completed = True
            lesson_progress.save()

            # Recalculer la progression globale de la formation
            ProgressService.recalculate_formation_progress(user, lesson.module.formation)

        return lesson_progress

    @staticmethod
    def save_video_position(user, lesson_id: int, position_seconds: int) -> LessonProgress:
        """
        Sauvegarde la position actuelle dans une vidéo.

        Appelé régulièrement (ex: toutes les 30 secondes) pendant la lecture vidéo.
        Permet à l'apprenant de reprendre la vidéo là où il s'est arrêté.

        Args:
            user:             L'apprenant
            lesson_id:        L'ID de la leçon vidéo
            position_seconds: Position actuelle en secondes (ex: 245 = 4min05sec)

        Returns:
            Le LessonProgress mis à jour avec la nouvelle position
        """
        lesson = Lesson.objects.get(pk=lesson_id)

        # update_fields=['video_position_seconds'] : met à jour SEULEMENT ce champ
        # Plus efficace que de sauvegarder tout l'objet (une seule colonne en SQL)
        lesson_progress, _ = LessonProgress.objects.get_or_create(
            user=user,
            lesson=lesson,
        )
        lesson_progress.video_position_seconds = position_seconds
        lesson_progress.save(update_fields=['video_position_seconds'])

        return lesson_progress

    @staticmethod
    def update_last_accessed(user, lesson_id: int) -> FormationProgress:
        """
        Met à jour la dernière leçon accédée par l'apprenant.

        Utilisé pour la fonctionnalité "Reprendre où j'en étais" :
        quand un apprenant revient sur une formation, on lui propose de
        repartir directement de la dernière leçon consultée.

        Args:
            user:      L'apprenant
            lesson_id: La leçon actuellement consultée

        Returns:
            Le FormationProgress mis à jour
        """
        lesson = Lesson.objects.select_related('module__formation').get(pk=lesson_id)
        formation = lesson.module.formation

        # Obtenir ou créer la progression globale pour cette formation
        formation_progress, _ = FormationProgress.objects.get_or_create(
            user=user,
            formation=formation,
        )

        # Mettre à jour la dernière leçon accédée
        # update_fields : ne touche que ces deux colonnes (plus efficace)
        formation_progress.last_accessed_lesson = lesson
        formation_progress.save(update_fields=['last_accessed_lesson', 'last_accessed_at'])

        return formation_progress

    @staticmethod
    def recalculate_formation_progress(user, formation) -> FormationProgress:
        """
        Recalcule et sauvegarde le pourcentage de progression d'un apprenant.

        Appelé après chaque leçon terminée ou quiz validé.

        Formule :
            percentage = (leçons_terminées + quiz_validés) / (total_leçons + total_quiz) × 100

        Cas particuliers :
            - Si total_leçons + total_quiz = 0 : percentage = 0 (évite la division par zéro)
            - is_completed = True seulement si 100% ET il y a du contenu

        Args:
            user:      L'apprenant
            formation: La Formation à recalculer

        Returns:
            Le FormationProgress mis à jour
        """
        # ── Compter les leçons ────────────────────────────────────────────────

        # Total de leçons dans toute la formation
        # (on passe par Module car Formation → Module → Lesson)
        total_lessons = Lesson.objects.filter(
            module__formation=formation
        ).count()

        # Leçons que cet apprenant a terminées (completed=True dans LessonProgress)
        completed_lessons = LessonProgress.objects.filter(
            user=user,
            lesson__module__formation=formation,
            completed=True,
        ).count()

        # ── Compter les quiz ──────────────────────────────────────────────────

        # Pour compter les quiz, on importe ici pour éviter les imports circulaires
        # (progress → quizzes → progress créerait une boucle d'import Python)
        try:
            from apps.quizzes.models import Quiz, QuizAttempt

            # Total de quiz dans la formation (un quiz par module au maximum)
            total_quizzes = Quiz.objects.filter(
                module__formation=formation
            ).count()

            # Quiz que l'apprenant a VALIDÉS (passed=True dans QuizAttempt)
            # .values('quiz') : dédoublonne par quiz (l'apprenant peut avoir plusieurs tentatives)
            # .distinct()     : s'assure de ne compter chaque quiz qu'une seule fois
            passed_quizzes = QuizAttempt.objects.filter(
                user=user,
                quiz__module__formation=formation,
                passed=True,
            ).values('quiz').distinct().count()

        except ImportError:
            # Si l'app quizzes n'est pas encore installée (ex: tests isolés)
            total_quizzes = 0
            passed_quizzes = 0

        # ── Calculer le pourcentage ────────────────────────────────────────────

        # Dénominateur = total leçons + total quiz
        total = total_lessons + total_quizzes

        if total > 0:
            # Calcul avec Decimal pour éviter les erreurs d'arrondi des floats
            # Exemple : 7/13 en float = 0.5384615... mais en Decimal = 53.85
            numerator = Decimal(completed_lessons + passed_quizzes)
            percentage = (numerator / Decimal(total) * Decimal(100)).quantize(
                Decimal('0.01')  # Arrondir à 2 décimales (ex: 66.67)
            )
        else:
            # Formation sans contenu (aucune leçon, aucun quiz)
            percentage = Decimal('0.00')

        # Une formation est "terminée" seulement si :
        #   1. Il y a du contenu (total > 0)
        #   2. L'apprenant a tout fait (100%)
        is_completed = (total > 0) and (percentage >= Decimal('100.00'))

        # ── Sauvegarder le résultat ────────────────────────────────────────────
        formation_progress, _ = FormationProgress.objects.get_or_create(
            user=user,
            formation=formation,
        )

        # Mettre à jour tous les champs dénormalisés d'un coup
        formation_progress.completed_lessons = completed_lessons
        formation_progress.total_lessons     = total_lessons
        formation_progress.passed_quizzes    = passed_quizzes
        formation_progress.total_quizzes     = total_quizzes
        formation_progress.percentage        = percentage
        formation_progress.is_completed      = is_completed
        formation_progress.save()

        return formation_progress
