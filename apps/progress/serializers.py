"""
Serializers pour l'app 'progress'.

  - FormationProgressSerializer : progression globale dans une formation
  - LessonProgressSerializer    : état d'une leçon
  - VideoPositionSerializer     : validation de la position vidéo
"""

from rest_framework import serializers

from .models import FormationProgress, LessonProgress


class LessonProgressSerializer(serializers.ModelSerializer):
    """État d'une leçon pour un apprenant."""

    lesson_titre = serializers.SerializerMethodField()
    lesson_type = serializers.SerializerMethodField()

    class Meta:
        model = LessonProgress
        fields = [
            'id', 'lesson', 'lesson_titre', 'lesson_type',
            'completed', 'video_position_seconds', 'last_accessed_at',
        ]
        read_only_fields = ['id', 'last_accessed_at']

    def get_lesson_titre(self, obj):
        return obj.lesson.titre if obj.lesson else None

    def get_lesson_type(self, obj):
        return obj.lesson.content_type if obj.lesson else None


class FormationProgressSerializer(serializers.ModelSerializer):
    """Progression globale dans une formation."""

    formation_titre = serializers.SerializerMethodField()
    formation_image = serializers.SerializerMethodField()
    last_accessed_lesson_titre = serializers.SerializerMethodField()

    class Meta:
        model = FormationProgress
        fields = [
            'id', 'formation', 'formation_titre', 'formation_image',
            'completed_lessons', 'total_lessons',
            'passed_quizzes', 'total_quizzes',
            'percentage', 'is_completed',
            'last_accessed_lesson', 'last_accessed_lesson_titre',
            'last_accessed_at',
        ]
        read_only_fields = ['id', 'last_accessed_at']

    def get_formation_titre(self, obj):
        return obj.formation.titre if obj.formation else None

    def get_formation_image(self, obj):
        if obj.formation and obj.formation.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.formation.image.url)
            return obj.formation.image.url
        return None

    def get_last_accessed_lesson_titre(self, obj):
        if obj.last_accessed_lesson:
            return obj.last_accessed_lesson.titre
        return None


class VideoPositionSerializer(serializers.Serializer):
    """Validation de la position dans une vidéo."""

    position_seconds = serializers.IntegerField(min_value=0, required=True)
