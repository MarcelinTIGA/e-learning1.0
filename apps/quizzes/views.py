"""
Views pour l'app 'quizzes'.

Endpoints disponibles :
  Gestion du quiz d'un module (formateur) :
    GET/POST   /api/quizzes/modules/<module_id>/quiz/      — Créer/voir le quiz d'un module
    GET/PUT/PATCH/DELETE /api/quizzes/<quiz_id>/           — Modifier le quiz

  Gestion des questions (formateur) :
    GET/POST   /api/quizzes/<quiz_id>/questions/           — Lister/créer des questions
    GET/PUT/PATCH/DELETE /api/quizzes/questions/<id>/      — Modifier une question

  Gestion des réponses (formateur) :
    GET/POST   /api/quizzes/questions/<question_id>/answers/  — Lister/créer des réponses
    GET/PUT/PATCH/DELETE /api/quizzes/answers/<id>/           — Modifier une réponse

  Côté apprenant :
    GET        /api/quizzes/<quiz_id>/attempt/             — Voir le quiz (sans is_correct)
    POST       /api/quizzes/<quiz_id>/submit/              — Soumettre ses réponses
    GET        /api/quizzes/<quiz_id>/history/             — Historique de ses tentatives
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Module
from apps.users.permissions import IsFormateurOrAdmin

from .models import Answer, Question, Quiz, QuizAttempt
from .serializers import (
    AnswerSerializer,
    AnswerWriteSerializer,
    QuestionSerializer,
    QuestionWriteSerializer,
    QuizAttemptSerializer,
    QuizSerializer,
    QuizStudentSerializer,
    QuizSubmissionSerializer,
    QuizWriteSerializer,
)
from .services import QuizGradingService


# ─────────────────────────────────────────────
# GESTION DU QUIZ (FORMATEUR)
# ─────────────────────────────────────────────

class QuizModuleView(generics.ListCreateAPIView):
    """
    GET  /api/quizzes/modules/<module_id>/quiz/  — Voir le quiz d'un module
    POST /api/quizzes/modules/<module_id>/quiz/  — Créer le quiz d'un module

    Un module ne peut avoir qu'un seul quiz (OneToOneField).
    """

    permission_classes = [IsFormateurOrAdmin]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return QuizWriteSerializer
        return QuizSerializer

    def get_queryset(self):
        """Retourne le quiz du module spécifié dans l'URL."""
        module_id = self.kwargs.get('module_id')
        return Quiz.objects.filter(module_id=module_id).prefetch_related('questions__answers')

    def perform_create(self, serializer):
        """
        Vérifie que le formateur est bien le propriétaire de la formation
        avant de créer le quiz.
        """
        module_id = self.kwargs.get('module_id')
        try:
            module = Module.objects.select_related('formation').get(pk=module_id)
        except Module.DoesNotExist:
            self.permission_denied(self.request, message="Module introuvable.")

        if not self.request.user.is_administrateur and module.formation.formateur != self.request.user:
            self.permission_denied(self.request, message="Vous n'êtes pas le formateur de ce module.")

        serializer.save(module=module)


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/quizzes/<id>/  — Voir le quiz complet (formateur)
    PATCH  /api/quizzes/<id>/  — Modifier le quiz
    DELETE /api/quizzes/<id>/  — Supprimer le quiz
    """

    permission_classes = [IsFormateurOrAdmin]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return QuizWriteSerializer
        return QuizSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_administrateur:
            return Quiz.objects.prefetch_related('questions__answers').all()
        # Le formateur ne voit que les quiz de ses propres formations
        return Quiz.objects.filter(
            module__formation__formateur=user
        ).prefetch_related('questions__answers')


# ─────────────────────────────────────────────
# GESTION DES QUESTIONS (FORMATEUR)
# ─────────────────────────────────────────────

class QuestionListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/quizzes/<quiz_id>/questions/  — Lister les questions
    POST /api/quizzes/<quiz_id>/questions/  — Ajouter une question
    """

    permission_classes = [IsFormateurOrAdmin]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return QuestionWriteSerializer
        return QuestionSerializer

    def get_queryset(self):
        quiz_id = self.kwargs.get('quiz_id')
        return Question.objects.filter(quiz_id=quiz_id).prefetch_related('answers')

    def perform_create(self, serializer):
        quiz_id = self.kwargs.get('quiz_id')
        try:
            quiz = Quiz.objects.select_related('module__formation').get(pk=quiz_id)
        except Quiz.DoesNotExist:
            self.permission_denied(self.request, message="Quiz introuvable.")

        if not self.request.user.is_administrateur and quiz.module.formation.formateur != self.request.user:
            self.permission_denied(self.request, message="Accès refusé.")

        serializer.save(quiz=quiz)


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Modifier ou supprimer une question spécifique."""

    permission_classes = [IsFormateurOrAdmin]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return QuestionWriteSerializer
        return QuestionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_administrateur:
            return Question.objects.prefetch_related('answers').all()
        return Question.objects.filter(
            quiz__module__formation__formateur=user
        ).prefetch_related('answers')


# ─────────────────────────────────────────────
# GESTION DES RÉPONSES (FORMATEUR)
# ─────────────────────────────────────────────

class AnswerListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/quizzes/questions/<question_id>/answers/  — Lister les réponses
    POST /api/quizzes/questions/<question_id>/answers/  — Ajouter une réponse
    """

    permission_classes = [IsFormateurOrAdmin]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AnswerWriteSerializer
        return AnswerSerializer

    def get_queryset(self):
        question_id = self.kwargs.get('question_id')
        return Answer.objects.filter(question_id=question_id)

    def perform_create(self, serializer):
        question_id = self.kwargs.get('question_id')
        try:
            question = Question.objects.select_related('quiz__module__formation').get(pk=question_id)
        except Question.DoesNotExist:
            self.permission_denied(self.request, message="Question introuvable.")

        if not self.request.user.is_administrateur and question.quiz.module.formation.formateur != self.request.user:
            self.permission_denied(self.request, message="Accès refusé.")

        serializer.save(question=question)


class AnswerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Modifier ou supprimer une réponse spécifique."""

    permission_classes = [IsFormateurOrAdmin]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return AnswerWriteSerializer
        return AnswerSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_administrateur:
            return Answer.objects.all()
        return Answer.objects.filter(question__quiz__module__formation__formateur=user)


# ─────────────────────────────────────────────
# CÔTÉ APPRENANT
# ─────────────────────────────────────────────

class QuizAttemptView(generics.RetrieveAPIView):
    """
    GET /api/quizzes/<quiz_id>/attempt/
    Affiche le quiz à l'apprenant SANS les bonnes réponses (is_correct masqué).
    L'apprenant doit être authentifié pour accéder au quiz.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QuizStudentSerializer

    def get_object(self):
        quiz_id = self.kwargs.get('quiz_id')
        try:
            return Quiz.objects.prefetch_related('questions__answers').get(pk=quiz_id)
        except Quiz.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Quiz introuvable.")


class QuizSubmitView(APIView):
    """
    POST /api/quizzes/<quiz_id>/submit/
    Soumet les réponses de l'apprenant et retourne le résultat corrigé.

    Corps de la requête :
        {
            "answers": [
                {"question_id": 1, "answer_id": 3},
                {"question_id": 2, "answer_id": 6}
            ]
        }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, quiz_id):
        # Valide les données soumises
        serializer = QuizSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Délègue la correction au service métier
            # Voir services.py pour le détail du calcul
            attempt = QuizGradingService.grade_submission(
                user=request.user,
                quiz_id=quiz_id,
                answers_data=serializer.validated_data['answers'],
            )
        except Quiz.DoesNotExist:
            return Response({'detail': "Quiz introuvable."}, status=status.HTTP_404_NOT_FOUND)

        # Retourne le résultat complet de la tentative
        result_serializer = QuizAttemptSerializer(attempt)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)


class QuizHistoryView(generics.ListAPIView):
    """
    GET /api/quizzes/<quiz_id>/history/
    Historique des tentatives de l'utilisateur connecté pour ce quiz.
    Permet de voir l'évolution de ses scores au fil des tentatives.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QuizAttemptSerializer

    def get_queryset(self):
        quiz_id = self.kwargs.get('quiz_id')
        # Ne retourne que les tentatives de l'utilisateur connecté (pas celles des autres)
        return QuizAttempt.objects.filter(
            user=self.request.user,
            quiz_id=quiz_id,
        ).prefetch_related('attempt_answers__question', 'attempt_answers__selected_answer')
