"""Administration Django pour l'app 'progress'."""

from django.contrib import admin

from .models import FormationProgress, LessonProgress


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'completed', 'video_position_seconds', 'last_accessed_at')
    list_filter = ('completed',)
    search_fields = ('user__email', 'lesson__titre')
    readonly_fields = ('last_accessed_at',)
    ordering = ('-last_accessed_at',)


@admin.register(FormationProgress)
class FormationProgressAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'formation', 'completed_lessons', 'total_lessons',
        'passed_quizzes', 'total_quizzes', 'percentage', 'is_completed', 'last_accessed_at',
    )
    list_filter = ('is_completed',)
    search_fields = ('user__email', 'formation__titre')
    # Champs dénormalisés : en lecture seule car gérés par ProgressService
    readonly_fields = (
        'completed_lessons', 'total_lessons',
        'passed_quizzes', 'total_quizzes',
        'percentage', 'is_completed', 'last_accessed_at',
    )
    ordering = ('-last_accessed_at',)
