"""
Modèles de l'app 'quizzes' — Système d'évaluation des apprenants.

Hiérarchie :
    Module (courses) ── 1:1 ── Quiz
                                └── 1:N ── Question
                                              └── 1:N ── Answer (choix de réponses)

    User ── 1:N ── QuizAttempt (tentative de quiz)
                       └── 1:N ── AttemptAnswer (réponse donnée par l'apprenant)

Règle pédagogique :
    Un apprenant doit VALIDER le quiz d'un module (score >= passing_score)
    pour pouvoir accéder au module suivant (déblocage progressif).
"""

from django.conf import settings
from django.db import models

from apps.courses.models import Module


class Quiz(models.Model):
    """
    Un quiz est lié à un module (relation 1:1).
    Chaque module a au plus un quiz. Le quiz doit être validé pour avancer.
    """

    # OneToOneField : garantit qu'un module ne peut avoir qu'un seul quiz
    # related_name='quiz' permet d'écrire module.quiz pour accéder au quiz d'un module
    module = models.OneToOneField(
        Module,
        on_delete=models.CASCADE,
        related_name='quiz',
        verbose_name="Module",
    )

    titre = models.CharField(max_length=200, verbose_name="Titre du quiz")

    # Score minimum (en %) pour valider le quiz et débloquer le module suivant
    # default=70 : l'apprenant doit avoir au moins 70% pour réussir
    passing_score = models.PositiveIntegerField(
        default=70,
        verbose_name="Score de validation (%)",
        help_text="Pourcentage minimum pour valider le quiz (ex: 70 = 70%)",
    )

    class Meta:
        db_table = 'quizzes'
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'

    def __str__(self):
        return f"Quiz : {self.titre} (module : {self.module.titre})"


class Question(models.Model):
    """
    Une question d'un quiz.
    Peut être de type QCM (choix multiples) ou Vrai/Faux.
    Chaque question a un nombre de points qui contribue au score final.
    """

    class QuestionType(models.TextChoices):
        QCM = 'qcm', 'QCM (choix multiples)'
        VRAI_FAUX = 'vrai_faux', 'Vrai / Faux'

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions',  # permet quiz.questions.all()
        verbose_name="Quiz",
    )

    text = models.TextField(verbose_name="Énoncé de la question")

    question_type = models.CharField(
        max_length=10,
        choices=QuestionType.choices,
        default=QuestionType.QCM,
        verbose_name="Type de question",
    )

    # order : position de la question dans le quiz (1, 2, 3...)
    order = models.PositiveIntegerField(default=1, verbose_name="Ordre")

    # points : valeur de cette question dans le score total
    # Ex: une question à 2 points vaut le double d'une question à 1 point
    points = models.PositiveIntegerField(default=1, verbose_name="Points")

    class Meta:
        db_table = 'questions'
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order} : {self.text[:60]}..."


class Answer(models.Model):
    """
    Un choix de réponse pour une question.
    Une question peut avoir plusieurs réponses, mais une seule est correcte (pour QCM/Vrai-Faux).
    Le champ is_correct permet la correction automatique.
    """

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers',  # permet question.answers.all()
        verbose_name="Question",
    )

    text = models.CharField(max_length=500, verbose_name="Texte de la réponse")

    # is_correct : True pour la bonne réponse, False pour les distracteurs
    # Ce champ est CACHÉ aux apprenants (voir QuizStudentSerializer)
    is_correct = models.BooleanField(default=False, verbose_name="Réponse correcte")

    class Meta:
        db_table = 'answers'
        verbose_name = 'Réponse'
        verbose_name_plural = 'Réponses'

    def __str__(self):
        correct_label = " ✓" if self.is_correct else ""
        return f"{self.text}{correct_label}"


class QuizAttempt(models.Model):
    """
    Une tentative de quiz par un apprenant.
    Enregistre le score obtenu et si le quiz a été validé.
    Un apprenant peut faire plusieurs tentatives (chaque tentative est enregistrée).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quiz_attempts',  # user.quiz_attempts.all()
        verbose_name="Apprenant",
    )

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='attempts',  # quiz.attempts.all()
        verbose_name="Quiz",
    )

    # Score en pourcentage (0 à 100)
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Score (%)",
    )

    # Points gagnés sur le total possible
    earned_points = models.PositiveIntegerField(default=0, verbose_name="Points obtenus")
    total_points = models.PositiveIntegerField(default=0, verbose_name="Total points possibles")

    # passed : True si score >= quiz.passing_score
    # Calculé automatiquement par QuizGradingService
    passed = models.BooleanField(default=False, verbose_name="Quiz validé")

    completed_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de tentative")

    class Meta:
        db_table = 'quiz_attempts'
        verbose_name = 'Tentative de quiz'
        verbose_name_plural = 'Tentatives de quiz'
        ordering = ['-completed_at']  # Les plus récentes en premier

    def __str__(self):
        status = "✓ Réussi" if self.passed else "✗ Échoué"
        return f"{self.user.email} — {self.quiz.titre} — {self.score}% ({status})"


class AttemptAnswer(models.Model):
    """
    La réponse donnée par l'apprenant pour une question lors d'une tentative.
    Permet de savoir quelle réponse a été choisie et si elle était correcte.
    """

    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='attempt_answers',  # attempt.attempt_answers.all()
        verbose_name="Tentative",
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        verbose_name="Question",
    )

    # La réponse sélectionnée par l'apprenant (peut être None si pas de réponse)
    selected_answer = models.ForeignKey(
        Answer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Réponse choisie",
    )

    # is_correct : copié depuis selected_answer.is_correct au moment de la correction
    # Stocké ici pour éviter de recalculer à chaque lecture
    is_correct = models.BooleanField(default=False, verbose_name="Réponse correcte")

    class Meta:
        db_table = 'attempt_answers'
        verbose_name = 'Réponse de tentative'
        verbose_name_plural = 'Réponses de tentative'

    def __str__(self):
        return f"Q{self.question.order} — {'✓' if self.is_correct else '✗'}"
