"""
Serializers pour l'app 'progress'.

Serializers disponibles :
    - LessonProgressSerializer          : état d'une leçon (lecture)
    - FormationProgressSerializer       : progression globale (lecture)
    - VideoPositionSerializer           : données pour sauvegarder position vidéo
    - MarkLessonCompleteSerializer      : (vide) pour marquer une leçon terminée
"""

from rest_framework import serializers

from .models import FormationProgress, LessonProgress


class LessonProgressSerializer(serializers.ModelSerializer):
    """
    État de progression pour une leçon spécifique.
    Inclut la position vidéo pour la reprise automatique.
    """

    # Afficher le titre de la leçon plutôt que son ID (plus lisible pour le frontend)
    lesson_titre = serializers.SerializerMethodField()

    class Meta:
        model = LessonProgress
        fields = (
            'id',
            'lesson',               # ID de la leçon
            'lesson_titre',         # Titre (calculé)
            'completed',            # True/False
            'video_position_seconds',  # Position dans la vidéo (0 si pas démarré)
            'last_accessed_at',     # Dernière visite (auto)
        )

    def get_lesson_titre(self, obj):
        return obj.lesson.titre


class FormationProgressSerializer(serializers.ModelSerializer):
    """
    Résumé global de la progression dans une formation.
    Retourné lors de la récupération du tableau de bord apprenant.
    """

    # Titre de la formation pour l'affichage
    formation_titre = serializers.SerializerMethodField()

    # Titre de la dernière leçon accédée (pour le bouton "Reprendre")
    # peut être null si l'apprenant n'a encore accédé à aucune leçon
    last_accessed_lesson_titre = serializers.SerializerMethodField()

    class Meta:
        model = FormationProgress
        fields = (
            'id',
            'formation',                    # ID de la formation
            'formation_titre',              # Titre (calculé)
            'completed_lessons',            # Ex: 7
            'total_lessons',                # Ex: 10
            'passed_quizzes',               # Ex: 2
            'total_quizzes',                # Ex: 3
            'percentage',                   # Ex: 69.23
            'is_completed',                 # True si 100%
            'last_accessed_lesson',         # ID de la dernière leçon
            'last_accessed_lesson_titre',   # Titre (calculé)
            'last_accessed_at',             # Date du dernier accès
        )

    def get_formation_titre(self, obj):
        return obj.formation.titre

    def get_last_accessed_lesson_titre(self, obj):
        """Retourne le titre de la dernière leçon accédée, ou None."""
        if obj.last_accessed_lesson:
            return obj.last_accessed_lesson.titre
        return None


class VideoPositionSerializer(serializers.Serializer):
    """
    Données envoyées pour sauvegarder la position dans une vidéo.

    Appelé régulièrement par le lecteur vidéo du frontend (ex: toutes les 30s).

    Corps JSON attendu :
        { "position_seconds": 245 }
    """

    # La position en secondes (doit être un entier positif)
    position_seconds = serializers.IntegerField(min_value=0)
