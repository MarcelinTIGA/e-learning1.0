"""
Serializers pour l'app 'quizzes'.

  - QuizSerializer           : lecture quiz (formateur)
  - QuizWriteSerializer      : écriture quiz
  - QuizStudentSerializer    : lecture quiz (apprenant, sans is_correct)
  - QuizSubmissionSerializer : validation des réponses soumises
  - QuizAttemptSerializer    : résultat d'une tentative
  - QuestionSerializer       : lecture question
  - QuestionWriteSerializer  : écriture question
  - AnswerSerializer         : lecture réponse
  - AnswerWriteSerializer    : écriture réponse
"""

from rest_framework import serializers

from .models import Answer, AttemptAnswer, Question, Quiz, QuizAttempt


# ─────────────────────────────────────────────
# ANSWER
# ─────────────────────────────────────────────

class AnswerSerializer(serializers.ModelSerializer):
    """Lecture d'une réponse (avec is_correct visible)."""

    class Meta:
        model = Answer
        fields = ['id', 'text', 'is_correct']
        read_only_fields = ['id']


class AnswerWriteSerializer(serializers.ModelSerializer):
    """Création/modification d'une réponse."""

    class Meta:
        model = Answer
        fields = ['id', 'text', 'is_correct']


# ─────────────────────────────────────────────
# QUESTION
# ─────────────────────────────────────────────

class QuestionSerializer(serializers.ModelSerializer):
    """Lecture d'une question avec ses réponses."""

    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'order', 'points', 'answers']
        read_only_fields = ['id']


class QuestionWriteSerializer(serializers.ModelSerializer):
    """Création/modification d'une question."""

    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'order', 'points']

    def validate_points(self, value):
        if value < 1:
            raise serializers.ValidationError("Les points doivent être >= 1.")
        return value


# ─────────────────────────────────────────────
# QUIZ
# ─────────────────────────────────────────────

class QuizSerializer(serializers.ModelSerializer):
    """Lecture d'un quiz avec questions et réponses (formateur)."""

    questions = QuestionSerializer(many=True, read_only=True)
    questions_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = ['id', 'module', 'titre', 'passing_score', 'questions', 'questions_count']
        read_only_fields = ['id']

    def get_questions_count(self, obj):
        return obj.questions.count() if hasattr(obj, 'questions') else 0


class QuizWriteSerializer(serializers.ModelSerializer):
    """Création/modification d'un quiz."""

    class Meta:
        model = Quiz
        fields = ['id', 'titre', 'passing_score']

    def validate_passing_score(self, value):
        if not (0 <= value <= 100):
            raise serializers.ValidationError("Le score de validation doit être entre 0 et 100.")
        return value


class QuizStudentSerializer(serializers.ModelSerializer):
    """Quiz affiché à l'apprenant (sans is_correct dans les réponses)."""

    questions = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = ['id', 'module', 'titre', 'passing_score', 'questions']
        read_only_fields = ['id']

    def get_questions(self, obj):
        """Retourne les questions avec réponses mais SANS is_correct."""
        questions_data = []
        for question in obj.questions.prefetch_related('answers').all():
            answers_data = []
            for answer in question.answers.all():
                answers_data.append({
                    'id': answer.id,
                    'text': answer.text,
                })
            questions_data.append({
                'id': question.id,
                'text': question.text,
                'question_type': question.question_type,
                'order': question.order,
                'points': question.points,
                'answers': answers_data,
            })
        return questions_data


# ─────────────────────────────────────────────
# ATTEMPT / SUBMISSION
# ─────────────────────────────────────────────

class QuizSubmissionAnswerSerializer(serializers.Serializer):
    """Réponse individuelle soumise par l'apprenant."""

    question_id = serializers.IntegerField(required=True)
    answer_id = serializers.IntegerField(required=True)


class QuizSubmissionSerializer(serializers.Serializer):
    """Validation des réponses soumises par l'apprenant."""

    answers = QuizSubmissionAnswerSerializer(many=True, required=True)

    def validate(self, attrs):
        if not attrs.get('answers'):
            raise serializers.ValidationError("Au moins une réponse est requise.")
        return attrs


class AttemptAnswerSerializer(serializers.ModelSerializer):
    """Réponse donnée lors d'une tentative."""

    question_titre = serializers.SerializerMethodField()
    selected_answer_text = serializers.SerializerMethodField()

    class Meta:
        model = AttemptAnswer
        fields = ['id', 'question', 'question_titre', 'selected_answer', 'selected_answer_text', 'is_correct']
        read_only_fields = ['id']

    def get_question_titre(self, obj):
        return obj.question.text[:80] if obj.question else None

    def get_selected_answer_text(self, obj):
        return obj.selected_answer.text if obj.selected_answer else None


class QuizAttemptSerializer(serializers.ModelSerializer):
    """Résultat d'une tentative de quiz."""

    attempt_answers = AttemptAnswerSerializer(many=True, read_only=True)
    quiz_titre = serializers.SerializerMethodField()

    class Meta:
        model = QuizAttempt
        fields = [
            'id', 'quiz', 'quiz_titre', 'score', 'earned_points',
            'total_points', 'passed', 'completed_at', 'attempt_answers',
        ]
        read_only_fields = ['id', 'completed_at']

    def get_quiz_titre(self, obj):
        return obj.quiz.titre if obj.quiz else None
