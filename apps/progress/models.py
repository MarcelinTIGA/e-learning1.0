"""
Modèles pour l'app 'progress' (Suivi de progression).

Pourquoi deux modèles de progression ?

    LessonProgress  : enregistre l'état de CHAQUE leçon pour UN apprenant
                      → "Est-ce que Jean a terminé la leçon 5 ?"
                      → "À quelle position s'est-il arrêté dans la vidéo ?"

    FormationProgress : résumé global de la progression d'un apprenant dans une formation
                       → "Jean a complété 7/10 leçons et 2/3 quiz = 56%"
                       → C'est un modèle DÉNORMALISÉ : on stocke le calcul déjà fait
                          pour éviter de le recalculer à chaque lecture.

Qu'est-ce que "dénormalisé" ?
    En base de données normalisée, on ne stocke pas les données qui peuvent être calculées.
    Ici on fait une exception volontaire : percentage, completed_lessons, etc. peuvent être
    recalculés depuis LessonProgress, mais c'est trop lent à la lecture.
    On stocke donc le résultat précalculé et on le met à jour via ProgressService.
"""

from django.conf import settings
from django.db import models


class LessonProgress(models.Model):
    """
    Suit l'avancement d'un apprenant pour UNE leçon spécifique.

    Créé automatiquement la première fois qu'un apprenant accède à une leçon.
    Mis à jour quand il marque la leçon comme terminée ou sauvegarde sa position vidéo.
    """

    # ── Relations ─────────────────────────────────────────────────────────────
    # L'apprenant dont on suit la progression
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_progresses',   # user.lesson_progresses.all()
    )

    # La leçon concernée
    lesson = models.ForeignKey(
        'courses.Lesson',
        on_delete=models.CASCADE,           # Si la leçon est supprimée, la progression aussi
        related_name='progresses',
    )

    # ── État de la leçon ──────────────────────────────────────────────────────
    # True = l'apprenant a terminé cette leçon (cliqué "marquer comme terminée")
    completed = models.BooleanField(default=False)

    # ── Pour les vidéos : reprise automatique ─────────────────────────────────
    # Sauvegarde la position en secondes dans la vidéo.
    # Exemple : 245 = l'apprenant s'est arrêté à 4 min 5 sec
    # 0 = vidéo pas encore démarrée
    video_position_seconds = models.PositiveIntegerField(default=0)

    # ── Date du dernier accès ─────────────────────────────────────────────────
    # auto_now=True : mis à jour automatiquement à chaque save()
    last_accessed_at = models.DateTimeField(auto_now=True)

    # ── Contrainte d'unicité ───────────────────────────────────────────────────
    class Meta:
        # Un seul enregistrement par (apprenant, leçon)
        # Évite les doublons et garantit l'intégrité des données
        unique_together = ('user', 'lesson')
        ordering = ['lesson__order']  # Triées par ordre de leçon

    def __str__(self):
        status = "✓" if self.completed else "○"
        return f"{status} {self.user.email} — {self.lesson.titre}"


class FormationProgress(models.Model):
    """
    Résumé global de la progression d'un apprenant dans une formation.

    C'est le modèle DÉNORMALISÉ : il stocke des totaux précalculés pour
    une lecture rapide (évite des requêtes complexes à chaque affichage).

    Mis à jour par ProgressService.recalculate_formation_progress() chaque fois
    qu'une leçon est terminée ou qu'un quiz est validé.

    Formule du pourcentage :
        percentage = (completed_lessons + passed_quizzes) / (total_lessons + total_quizzes) × 100

    Exemple :
        Formation avec 10 leçons et 3 quiz
        Apprenant a terminé 7 leçons et validé 2 quiz
        → percentage = (7 + 2) / (10 + 3) × 100 = 69.2%
    """

    # ── Relations ─────────────────────────────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='formation_progresses',
    )

    formation = models.ForeignKey(
        'courses.Formation',
        on_delete=models.CASCADE,
        related_name='progresses',
    )

    # ── Compteurs (dénormalisés) ───────────────────────────────────────────────
    # Ces valeurs sont recalculées par ProgressService, ne pas les modifier directement

    # Nombre de leçons terminées par l'apprenant dans cette formation
    completed_lessons = models.PositiveIntegerField(default=0)

    # Nombre total de leçons dans la formation (mis à jour lors du recalcul)
    total_lessons = models.PositiveIntegerField(default=0)

    # Nombre de quiz validés (score ≥ passing_score)
    passed_quizzes = models.PositiveIntegerField(default=0)

    # Nombre total de quiz dans la formation
    total_quizzes = models.PositiveIntegerField(default=0)

    # ── Résultat du calcul ────────────────────────────────────────────────────
    # Pourcentage global d'avancement (0.00 à 100.00)
    # Decimal pour l'affichage précis (ex: 66.67%)
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    # True = l'apprenant a 100% (toutes leçons + tous quiz)
    # Déclenche la génération du certificat (via signal dans certificates/signals.py)
    is_completed = models.BooleanField(default=False)

    # ── Dernière leçon accédée (pour la reprise automatique) ──────────────────
    # Null possible : l'apprenant n'a encore accédé à aucune leçon
    last_accessed_lesson = models.ForeignKey(
        'courses.Lesson',
        on_delete=models.SET_NULL,  # Si la leçon est supprimée, on remet à null
        null=True,
        blank=True,
        related_name='+',           # '+' = pas de related_name inverse (inutile ici)
    )

    # ── Date du dernier accès ─────────────────────────────────────────────────
    last_accessed_at = models.DateTimeField(auto_now=True)

    # ── Contrainte d'unicité ───────────────────────────────────────────────────
    class Meta:
        # Un seul résumé par (apprenant, formation)
        unique_together = ('user', 'formation')
        ordering = ['-last_accessed_at']  # Plus récents en premier (évite UnorderedObjectListWarning)

    def __str__(self):
        return f"{self.user.email} — {self.formation.titre} ({self.percentage}%)"
