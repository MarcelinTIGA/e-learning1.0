"""Administration Django pour l'app 'quizzes'."""

from django.contrib import admin

from .models import Answer, AttemptAnswer, Question, Quiz, QuizAttempt


class AnswerInline(admin.TabularInline):
    """Affiche les réponses directement dans la page de détail d'une question."""

    model = Answer
    extra = 0
    fields = ('text', 'is_correct')


class QuestionInline(admin.TabularInline):
    """Affiche les questions directement dans la page de détail d'un quiz."""

    model = Question
    extra = 0
    fields = ('text', 'question_type', 'order', 'points')
    ordering = ('order',)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('titre', 'module', 'passing_score')
    search_fields = ('titre', 'module__titre')
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'quiz', 'question_type', 'order', 'points')
    list_filter = ('question_type',)
    search_fields = ('text', 'quiz__titre')
    inlines = [AnswerInline]
    ordering = ('quiz', 'order')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('text', 'question', 'is_correct')
    list_filter = ('is_correct',)
    search_fields = ('text',)


class AttemptAnswerInline(admin.TabularInline):
    """Affiche les réponses de l'apprenant dans le détail d'une tentative."""

    model = AttemptAnswer
    extra = 0
    readonly_fields = ('question', 'selected_answer', 'is_correct')
    can_delete = False  # On ne supprime pas les réponses individuelles


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'earned_points', 'total_points', 'passed', 'completed_at')
    list_filter = ('passed',)
    search_fields = ('user__email', 'quiz__titre')
    readonly_fields = ('score', 'earned_points', 'total_points', 'passed', 'completed_at')
    inlines = [AttemptAnswerInline]
    ordering = ('-completed_at',)
