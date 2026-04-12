"""
Serializers pour l'app 'quizzes'.

On distingue deux "vues" du quiz selon l'utilisateur :
    - Vue FORMATEUR : voit is_correct des réponses (pour corriger/créer le quiz)
    - Vue APPRENANT : ne voit PAS is_correct (pour éviter la triche)

Serializers disponibles :
    - AnswerSerializer          : réponse avec is_correct (formateur)
    - AnswerStudentSerializer   : réponse SANS is_correct (apprenant)
    - QuestionSerializer        : question avec réponses (formateur)
    - QuestionStudentSerializer : question avec réponses masquées (apprenant)
    - QuizSerializer            : quiz complet pour formateur
    - QuizStudentSerializer     : quiz pour apprenant (is_correct caché)
    - QuizSubmissionSerializer  : données soumises par l'apprenant
    - QuizAttemptSerializer     : résultat d'une tentative
"""

from rest_framework import serializers

from .models import Answer, AttemptAnswer, Question, Quiz, QuizAttempt


# ─────────────────────────────────────────────
# RÉPONSES
# ─────────────────────────────────────────────

class AnswerSerializer(serializers.ModelSerializer):
    """
    Serializer de réponse COMPLET — réservé aux formateurs.
    Inclut is_correct (la bonne réponse est visible).
    """

    class Meta:
        model = Answer
        fields = ('id', 'text', 'is_correct')


class AnswerStudentSerializer(serializers.ModelSerializer):
    """
    Serializer de réponse pour les APPRENANTS.
    is_correct est intentionnellement EXCLU pour éviter la triche.
    """

    class Meta:
        model = Answer
        fields = ('id', 'text')  # Pas de 'is_correct' !


class AnswerWriteSerializer(serializers.ModelSerializer):
    """Serializer pour créer/modifier une réponse (formateur)."""

    class Meta:
        model = Answer
        fields = ('id', 'question', 'text', 'is_correct')


# ─────────────────────────────────────────────
# QUESTIONS
# ─────────────────────────────────────────────

class QuestionSerializer(serializers.ModelSerializer):
    """
    Serializer de question COMPLET — réservé aux formateurs.
    Inclut les réponses avec is_correct.
    """

    # many=True : une liste de réponses imbriquées
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'text', 'question_type', 'order', 'points', 'answers')


class QuestionStudentSerializer(serializers.ModelSerializer):
    """
    Serializer de question pour les APPRENANTS.
    Les réponses ne montrent pas is_correct.
    """

    # AnswerStudentSerializer : version masquée (sans is_correct)
    answers = AnswerStudentSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'text', 'question_type', 'order', 'points', 'answers')


class QuestionWriteSerializer(serializers.ModelSerializer):
    """Serializer pour créer/modifier une question (formateur)."""

    class Meta:
        model = Question
        fields = ('id', 'quiz', 'text', 'question_type', 'order', 'points')


# ─────────────────────────────────────────────
# QUIZ
# ─────────────────────────────────────────────

class QuizSerializer(serializers.ModelSerializer):
    """
    Serializer de quiz COMPLET — réservé aux formateurs.
    Inclut toutes les questions avec leurs réponses (is_correct visible).
    """

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ('id', 'module', 'titre', 'passing_score', 'questions')


class QuizStudentSerializer(serializers.ModelSerializer):
    """
    Serializer de quiz pour les APPRENANTS.
    Les bonnes réponses (is_correct) sont masquées.
    """

    # QuestionStudentSerializer : version masquée
    questions = QuestionStudentSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ('id', 'titre', 'passing_score', 'questions')
        # 'module' exclu : l'apprenant n'en a pas besoin ici


class QuizWriteSerializer(serializers.ModelSerializer):
    """Serializer pour créer/modifier un quiz (formateur)."""

    class Meta:
        model = Quiz
        fields = ('id', 'module', 'titre', 'passing_score')

    def validate_module(self, module):
        """
        Vérifie qu'un quiz n'existe pas déjà pour ce module.
        Chaque module ne peut avoir qu'un seul quiz (OneToOneField).
        On exclut l'instance actuelle pour permettre les modifications (PATCH).
        """
        queryset = Quiz.objects.filter(module=module)

        # self.instance : l'objet existant lors d'une mise à jour (PATCH/PUT)
        # On l'exclut pour ne pas bloquer la modification d'un quiz existant
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("Un quiz existe déjà pour ce module.")
        return module


# ─────────────────────────────────────────────
# SOUMISSION DE QUIZ
# ─────────────────────────────────────────────

class AnswerSubmissionSerializer(serializers.Serializer):
    """
    Représente la réponse à UNE question dans une soumission.
    Structure attendue : {"question_id": 1, "answer_id": 3}
    """

    question_id = serializers.IntegerField()
    answer_id = serializers.IntegerField(required=False, allow_null=True)


class QuizSubmissionSerializer(serializers.Serializer):
    """
    Données envoyées par l'apprenant lors de la soumission d'un quiz.

    Structure JSON attendue :
        {
            "answers": [
                {"question_id": 1, "answer_id": 3},
                {"question_id": 2, "answer_id": 7},
                ...
            ]
        }
    """

    # many=True : une liste de réponses (une par question)
    answers = AnswerSubmissionSerializer(many=True)

    def validate_answers(self, value):
        """Vérifie qu'au moins une réponse est fournie."""
        if not value:
            raise serializers.ValidationError("Vous devez fournir au moins une réponse.")
        return value


# ─────────────────────────────────────────────
# RÉSULTAT D'UNE TENTATIVE
# ─────────────────────────────────────────────

class AttemptAnswerSerializer(serializers.ModelSerializer):
    """
    Détail d'une réponse donnée lors d'une tentative.
    Permet à l'apprenant de voir ses erreurs après correction.
    """

    # SerializerMethodField : champ calculé dynamiquement
    question_text = serializers.SerializerMethodField()
    selected_answer_text = serializers.SerializerMethodField()

    class Meta:
        model = AttemptAnswer
        fields = ('question_text', 'selected_answer_text', 'is_correct')

    def get_question_text(self, obj):
        """Retourne le texte de la question."""
        return obj.question.text

    def get_selected_answer_text(self, obj):
        """Retourne le texte de la réponse choisie (ou None si pas de réponse)."""
        if obj.selected_answer:
            return obj.selected_answer.text
        return None


class QuizAttemptSerializer(serializers.ModelSerializer):
    """
    Résultat complet d'une tentative de quiz.
    Retourné après la soumission et disponible dans l'historique.
    """

    # Détail de chaque réponse donnée (avec correction)
    attempt_answers = AttemptAnswerSerializer(many=True, read_only=True)

    # Nom du quiz pour l'affichage
    quiz_titre = serializers.SerializerMethodField()

    class Meta:
        model = QuizAttempt
        fields = (
            'id', 'quiz_titre', 'score', 'earned_points',
            'total_points', 'passed', 'completed_at', 'attempt_answers',
        )

    def get_quiz_titre(self, obj):
        return obj.quiz.titre
