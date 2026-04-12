"""
Signaux Django pour l'app 'progress'.

Qu'est-ce qu'un signal Django ?
    Un signal est un mécanisme de communication entre composants découplés.
    Quand un événement se produit dans une app (ex: un quiz est validé),
    Django "envoie" un signal. D'autres apps peuvent "écouter" ce signal
    et réagir sans que l'app émettrice ne les connaisse.

    C'est comme un système d'événements :
        App quizzes : "Hey, un quiz vient d'être soumis !" (signal post_save)
        App progress : "Super, je vais recalculer la progression."

    Avantage : l'app 'quizzes' ne connaît pas l'app 'progress'.
               Si on retire 'progress', 'quizzes' continue de fonctionner.

Signal implémenté ici :
    post_save sur QuizAttempt :
        Quand un QuizAttempt est sauvegardé et que passed=True,
        on recalcule automatiquement la progression de la formation.

Comment les signaux sont connectés :
    Dans apps/progress/apps.py, on override la méthode ready() pour importer
    ce fichier. Django appelle ready() au démarrage de l'app.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# @receiver(signal, sender=Model) :
#   Connecte cette fonction au signal 'post_save' émis par QuizAttempt.
#   Chaque fois qu'un QuizAttempt est créé ou modifié, cette fonction est appelée.
@receiver(post_save, sender='quizzes.QuizAttempt')
def update_progress_on_quiz_attempt(sender, instance, created, **kwargs):
    """
    Recalcule la progression d'une formation quand un quiz est soumis.

    Args:
        sender:   La classe qui a émis le signal (QuizAttempt)
        instance: L'objet QuizAttempt qui vient d'être sauvegardé
        created:  True si c'est une nouvelle création, False si c'est une mise à jour
        **kwargs: Arguments supplémentaires passés par Django (toujours inclure)

    Note : On recalcule SEULEMENT si la tentative vient d'être créée (created=True)
           pour éviter des recalculs répétés lors des mises à jour mineures.
    """
    # On ne recalcule que lors de la création d'une nouvelle tentative
    # (created=True = INSERT en SQL, False = UPDATE)
    if not created:
        return

    try:
        from .services import ProgressService

        # instance.quiz.module.formation = remonter la hiérarchie jusqu'à la formation
        # select_related a déjà été fait dans QuizGradingService.grade_submission
        formation = instance.quiz.module.formation

        ProgressService.recalculate_formation_progress(
            user=instance.user,
            formation=formation,
        )

        logger.info(
            f"[Signal] Progression recalculée : {instance.user.email} → "
            f"{formation.titre} (quiz: {instance.quiz.titre}, passed={instance.passed})"
        )

    except Exception as e:
        # On ne laisse JAMAIS un signal planter l'application principale.
        # Si le recalcul échoue, on logue l'erreur mais le quiz est quand même sauvegardé.
        logger.error(f"[Signal] Erreur lors du recalcul de progression : {e}")
