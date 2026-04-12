"""
Services pour l'app 'quizzes'.

Contient la logique métier de correction des quiz.
"""

from decimal import Decimal

from .models import Answer, AttemptAnswer, Question, Quiz, QuizAttempt


class QuizGradingService:
    """Correction automatique des quiz et gestion des tentatives."""

    @staticmethod
    def grade_submission(user, quiz_id, answers_data):
        """
        Corrige une soumission de quiz et crée une tentative.

        Args:
            user: l'apprenant qui soumet
            quiz_id: ID du quiz
            answers_data: liste de dicts [{'question_id': N, 'answer_id': N}, ...]

        Returns:
            QuizAttempt: la tentative corrigée

        Raises:
            ValueError: si le quiz est introuvable
        """
        try:
            quiz = Quiz.objects.prefetch_related('questions__answers').get(pk=quiz_id)
        except Quiz.DoesNotExist:
            raise ValueError("Quiz introuvable.")

        # Créer la tentative
        attempt = QuizAttempt.objects.create(
            user=user,
            quiz=quiz,
            score=Decimal('0.00'),
            earned_points=0,
            total_points=0,
            passed=False,
        )

        total_points = 0
        earned_points = 0

        # Traiter chaque réponse
        for answer_data in answers_data:
            question_id = answer_data['question_id']
            selected_answer_id = answer_data['answer_id']

            try:
                question = Question.objects.get(pk=question_id, quiz=quiz)
            except Question.DoesNotExist:
                continue

            total_points += question.points

            try:
                selected_answer = Answer.objects.get(pk=selected_answer_id, question=question)
            except Answer.DoesNotExist:
                # Réponse invalide → incorrecte
                AttemptAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_answer=None,
                    is_correct=False,
                )
                continue

            is_correct = selected_answer.is_correct
            if is_correct:
                earned_points += question.points

            AttemptAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_answer=selected_answer,
                is_correct=is_correct,
            )

        # Calculer le score
        attempt.total_points = total_points
        attempt.earned_points = earned_points

        if total_points > 0:
            score = Decimal(str(earned_points / total_points * 100)).quantize(Decimal('0.01'))
        else:
            score = Decimal('0.00')

        attempt.score = score
        attempt.passed = score >= quiz.passing_score
        attempt.save()

        return attempt

    @staticmethod
    def get_user_best_attempt(user, quiz_id):
        """
        Retourne la meilleure tentative d'un utilisateur pour un quiz.

        Args:
            user: l'apprenant
            quiz_id: ID du quiz

        Returns:
            QuizAttempt ou None
        """
        return (
            QuizAttempt.objects
            .filter(user=user, quiz_id=quiz_id)
            .order_by('-score')
            .first()
        )

    @staticmethod
    def get_user_attempts(user, quiz_id):
        """
        Retourne toutes les tentatives d'un utilisateur pour un quiz.

        Args:
            user: l'apprenant
            quiz_id: ID du quiz

        Returns:
            Queryset de QuizAttempt
        """
        return QuizAttempt.objects.filter(
            user=user,
            quiz_id=quiz_id,
        ).prefetch_related('attempt_answers__question', 'attempt_answers__selected_answer').order_by('-completed_at')
