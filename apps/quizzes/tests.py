"""
Tests pour l'app 'quizzes'.

Organisation :
  - QuizGradingServiceTest  : Tests du service de correction automatique
  - QuizAccessTest          : Tests de la logique de déblocage progressif
  - QuizManageTest          : Tests CRUD des quiz/questions/réponses (formateur)
  - QuizStudentTest         : Tests du côté apprenant (soumission, masquage is_correct)
  - QuizHistoryTest         : Tests de l'historique des tentatives
"""

from decimal import Decimal

from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Category, Formation, Lesson, Module
from apps.users.models import User

from .models import Answer, AttemptAnswer, Question, Quiz, QuizAttempt
from .services import QuizGradingService, can_access_module


def get_auth_client(user):
    """Crée un client API authentifié via JWT."""
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


def create_quiz_with_questions(module, titre="Test Quiz", passing_score=70):
    """
    Fonction utilitaire : crée un quiz complet avec 2 questions et leurs réponses.
    Utilisé dans plusieurs tests pour éviter la répétition du code.

    Structure créée :
        Quiz "Test Quiz"
          ├── Question 1 (1 point) : choix A (correct), choix B, choix C
          └── Question 2 (1 point) : Vrai (correct), Faux
    """
    quiz = Quiz.objects.create(module=module, titre=titre, passing_score=passing_score)

    # Question 1 — QCM
    q1 = Question.objects.create(quiz=quiz, text="Question 1", order=1, points=1)
    Answer.objects.create(question=q1, text="Réponse A (correcte)", is_correct=True)
    Answer.objects.create(question=q1, text="Réponse B", is_correct=False)
    Answer.objects.create(question=q1, text="Réponse C", is_correct=False)

    # Question 2 — Vrai/Faux
    q2 = Question.objects.create(quiz=quiz, text="Question 2", order=2, points=1,
                                  question_type=Question.QuestionType.VRAI_FAUX)
    Answer.objects.create(question=q2, text="Vrai", is_correct=True)
    Answer.objects.create(question=q2, text="Faux", is_correct=False)

    return quiz


# ═══════════════════════════════════════════════
# TESTS DU SERVICE DE CORRECTION
# ═══════════════════════════════════════════════

class QuizGradingServiceTest(APITestCase):
    """
    Tests unitaires du QuizGradingService.
    Ces tests vérifient la logique de calcul du score, indépendamment de l'API.
    """

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Jean', last_name='Formateur',
            role=User.Role.FORMATEUR,
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Marie', last_name='Apprenant',
        )
        self.formation = Formation.objects.create(
            formateur=self.formateur, titre='Formation', description='...'
        )
        self.module = Module.objects.create(
            formation=self.formation, titre='Module 1', order=1
        )
        # Crée le quiz avec 2 questions de 1 point chacune (total = 2 points)
        self.quiz = create_quiz_with_questions(self.module)

    def test_perfect_score(self):
        """100% des bonnes réponses → score = 100%, quiz validé."""
        # Récupère les IDs des bonnes réponses
        q1 = self.quiz.questions.get(order=1)
        q2 = self.quiz.questions.get(order=2)
        correct_q1 = q1.answers.get(is_correct=True)
        correct_q2 = q2.answers.get(is_correct=True)

        attempt = QuizGradingService.grade_submission(
            user=self.apprenant,
            quiz_id=self.quiz.id,
            answers_data=[
                {'question_id': q1.id, 'answer_id': correct_q1.id},
                {'question_id': q2.id, 'answer_id': correct_q2.id},
            ],
        )

        self.assertEqual(attempt.score, Decimal('100.00'))
        self.assertEqual(attempt.earned_points, 2)
        self.assertEqual(attempt.total_points, 2)
        self.assertTrue(attempt.passed)

    def test_zero_score(self):
        """0% de bonnes réponses → score = 0%, quiz non validé."""
        q1 = self.quiz.questions.get(order=1)
        q2 = self.quiz.questions.get(order=2)
        wrong_q1 = q1.answers.filter(is_correct=False).first()
        wrong_q2 = q2.answers.get(is_correct=False)

        attempt = QuizGradingService.grade_submission(
            user=self.apprenant,
            quiz_id=self.quiz.id,
            answers_data=[
                {'question_id': q1.id, 'answer_id': wrong_q1.id},
                {'question_id': q2.id, 'answer_id': wrong_q2.id},
            ],
        )

        self.assertEqual(attempt.score, Decimal('0.00'))
        self.assertEqual(attempt.earned_points, 0)
        self.assertFalse(attempt.passed)

    def test_partial_score(self):
        """1 bonne réponse sur 2 → score = 50%, non validé (seuil = 70%)."""
        q1 = self.quiz.questions.get(order=1)
        q2 = self.quiz.questions.get(order=2)
        correct_q1 = q1.answers.get(is_correct=True)
        wrong_q2 = q2.answers.get(is_correct=False)

        attempt = QuizGradingService.grade_submission(
            user=self.apprenant,
            quiz_id=self.quiz.id,
            answers_data=[
                {'question_id': q1.id, 'answer_id': correct_q1.id},
                {'question_id': q2.id, 'answer_id': wrong_q2.id},
            ],
        )

        self.assertEqual(attempt.score, Decimal('50.00'))
        self.assertFalse(attempt.passed)  # 50% < 70% (passing_score)

    def test_passing_score_custom(self):
        """Quiz avec seuil de validation à 50% : 50% de bonnes réponses → validé."""
        # Crée un nouveau module pour ce quiz avec seuil différent
        module2 = Module.objects.create(
            formation=self.formation, titre='Module 2', order=2
        )
        quiz_easy = create_quiz_with_questions(module2, passing_score=50)

        q1 = quiz_easy.questions.get(order=1)
        q2 = quiz_easy.questions.get(order=2)
        correct_q1 = q1.answers.get(is_correct=True)
        wrong_q2 = q2.answers.get(is_correct=False)

        attempt = QuizGradingService.grade_submission(
            user=self.apprenant,
            quiz_id=quiz_easy.id,
            answers_data=[
                {'question_id': q1.id, 'answer_id': correct_q1.id},
                {'question_id': q2.id, 'answer_id': wrong_q2.id},
            ],
        )

        self.assertEqual(attempt.score, Decimal('50.00'))
        self.assertTrue(attempt.passed)  # 50% >= 50% (passing_score)

    def test_attempt_answers_created(self):
        """Chaque réponse soumise crée un AttemptAnswer en base."""
        q1 = self.quiz.questions.get(order=1)
        q2 = self.quiz.questions.get(order=2)

        attempt = QuizGradingService.grade_submission(
            user=self.apprenant,
            quiz_id=self.quiz.id,
            answers_data=[
                {'question_id': q1.id, 'answer_id': q1.answers.first().id},
                {'question_id': q2.id, 'answer_id': q2.answers.first().id},
            ],
        )

        # Doit avoir créé exactement 2 AttemptAnswer (une par question)
        self.assertEqual(attempt.attempt_answers.count(), 2)

    def test_no_answer_for_question(self):
        """Une question sans réponse est comptée comme incorrecte (0 point)."""
        q1 = self.quiz.questions.get(order=1)
        correct_q1 = q1.answers.get(is_correct=True)

        attempt = QuizGradingService.grade_submission(
            user=self.apprenant,
            quiz_id=self.quiz.id,
            answers_data=[
                {'question_id': q1.id, 'answer_id': correct_q1.id},
                # q2 non répondue
            ],
        )

        # 1 point sur 2 → 50%
        self.assertEqual(attempt.earned_points, 1)


# ═══════════════════════════════════════════════
# TESTS DU DÉBLOCAGE PROGRESSIF
# ═══════════════════════════════════════════════

class QuizAccessTest(APITestCase):
    """
    Tests de la logique de déblocage progressif des modules.
    Le module N+1 n'est accessible que si le module N est complété (quiz validé).
    """

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Jean', last_name='Formateur',
            role=User.Role.FORMATEUR,
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Marie', last_name='Apprenant',
        )
        self.formation = Formation.objects.create(
            formateur=self.formateur, titre='Formation', description='...'
        )
        # Module 1 avec quiz
        self.module1 = Module.objects.create(
            formation=self.formation, titre='Module 1', order=1
        )
        self.quiz1 = create_quiz_with_questions(self.module1)

        # Module 2 (dépend de module1)
        self.module2 = Module.objects.create(
            formation=self.formation, titre='Module 2', order=2
        )

    def test_first_module_always_accessible(self):
        """Le premier module (order=1) est toujours accessible."""
        self.assertTrue(can_access_module(self.apprenant, self.module1))

    def test_second_module_blocked_without_quiz_pass(self):
        """Le module 2 est bloqué si le quiz du module 1 n'est pas validé."""
        self.assertFalse(can_access_module(self.apprenant, self.module2))

    def test_second_module_accessible_after_quiz_pass(self):
        """Le module 2 est accessible après avoir validé le quiz du module 1."""
        # Simule une tentative réussie
        QuizAttempt.objects.create(
            user=self.apprenant,
            quiz=self.quiz1,
            score=Decimal('100.00'),
            earned_points=2,
            total_points=2,
            passed=True,
        )
        self.assertTrue(can_access_module(self.apprenant, self.module2))

    def test_second_module_blocked_after_failed_quiz(self):
        """Le module 2 reste bloqué après une tentative échouée du quiz 1."""
        QuizAttempt.objects.create(
            user=self.apprenant,
            quiz=self.quiz1,
            score=Decimal('50.00'),
            earned_points=1,
            total_points=2,
            passed=False,  # Échec
        )
        self.assertFalse(can_access_module(self.apprenant, self.module2))

    def test_module_without_quiz_not_blocking(self):
        """
        Si le module 1 n'a pas de quiz, le module 2 est accessible
        (uniquement les leçons doivent être complétées).
        """
        # Supprime le quiz du module 1
        self.quiz1.delete()

        # Sans app progress installée, le module 2 est accessible
        self.assertTrue(can_access_module(self.apprenant, self.module2))


# ═══════════════════════════════════════════════
# TESTS DE GESTION (FORMATEUR)
# ═══════════════════════════════════════════════

class QuizManageTest(APITestCase):
    """Tests CRUD des quiz, questions et réponses par le formateur."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Jean', last_name='Formateur',
            role=User.Role.FORMATEUR,
        )
        self.autre_formateur = User.objects.create_user(
            email='autre@test.com', password='Pass123!',
            first_name='Alice', last_name='Autre',
            role=User.Role.FORMATEUR,
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Bob', last_name='Apprenant',
        )
        self.formation = Formation.objects.create(
            formateur=self.formateur, titre='Formation', description='...'
        )
        self.module = Module.objects.create(
            formation=self.formation, titre='Module 1', order=1
        )

    def test_formateur_can_create_quiz(self):
        """Un formateur peut créer un quiz pour son module."""
        client = get_auth_client(self.formateur)
        response = client.post(
            f'/api/quizzes/modules/{self.module.id}/quiz/',
            {'module': self.module.id, 'titre': 'Quiz Test', 'passing_score': 70},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Quiz.objects.filter(module=self.module).exists())

    def test_apprenant_cannot_create_quiz(self):
        """Un apprenant ne peut pas créer de quiz."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            f'/api/quizzes/modules/{self.module.id}/quiz/',
            {'module': self.module.id, 'titre': 'Quiz Tentative', 'passing_score': 50},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_autre_formateur_cannot_create_quiz_on_other_module(self):
        """Un formateur ne peut pas créer de quiz sur le module d'un autre."""
        client = get_auth_client(self.autre_formateur)
        response = client.post(
            f'/api/quizzes/modules/{self.module.id}/quiz/',
            {'module': self.module.id, 'titre': 'Quiz Volé', 'passing_score': 70},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_formateur_can_add_question(self):
        """Un formateur peut ajouter une question à son quiz."""
        quiz = Quiz.objects.create(module=self.module, titre='Quiz', passing_score=70)
        client = get_auth_client(self.formateur)
        response = client.post(
            f'/api/quizzes/{quiz.id}/questions/',
            {'quiz': quiz.id, 'text': 'Quelle est la capitale de la France ?',
             'question_type': 'qcm', 'order': 1, 'points': 2},
            format='json',
        )
        self.assertEqual(response.status_code, 201)

    def test_formateur_can_add_answer(self):
        """Un formateur peut ajouter des réponses à une question."""
        quiz = Quiz.objects.create(module=self.module, titre='Quiz', passing_score=70)
        question = Question.objects.create(quiz=quiz, text='Question ?', order=1)
        client = get_auth_client(self.formateur)

        response = client.post(
            f'/api/quizzes/questions/{question.id}/answers/',
            {'question': question.id, 'text': 'Paris', 'is_correct': True},
            format='json',
        )
        self.assertEqual(response.status_code, 201)

    def test_cannot_create_two_quizzes_for_same_module(self):
        """Un module ne peut avoir qu'un seul quiz."""
        Quiz.objects.create(module=self.module, titre='Quiz 1', passing_score=70)
        client = get_auth_client(self.formateur)

        response = client.post(
            f'/api/quizzes/modules/{self.module.id}/quiz/',
            {'module': self.module.id, 'titre': 'Quiz 2', 'passing_score': 60},
            format='json',
        )
        # Doit retourner une erreur de validation
        self.assertEqual(response.status_code, 400)


# ═══════════════════════════════════════════════
# TESTS CÔTÉ APPRENANT
# ═══════════════════════════════════════════════

class QuizStudentTest(APITestCase):
    """Tests du côté apprenant : soumission, masquage des réponses."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Jean', last_name='Formateur',
            role=User.Role.FORMATEUR,
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Marie', last_name='Apprenant',
        )
        self.formation = Formation.objects.create(
            formateur=self.formateur, titre='Formation', description='...'
        )
        self.module = Module.objects.create(
            formation=self.formation, titre='Module 1', order=1
        )
        self.quiz = create_quiz_with_questions(self.module)

    def test_student_cannot_see_is_correct(self):
        """
        L'apprenant ne doit pas voir le champ is_correct dans les réponses.
        C'est crucial pour empêcher la triche.
        """
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/quizzes/{self.quiz.id}/attempt/')
        self.assertEqual(response.status_code, 200)

        # Vérifie que is_correct n'est PAS présent dans les réponses
        for question in response.data['questions']:
            for answer in question['answers']:
                self.assertNotIn('is_correct', answer)

    def test_student_can_submit_quiz(self):
        """Un apprenant peut soumettre ses réponses et obtenir un score."""
        client = get_auth_client(self.apprenant)
        q1 = self.quiz.questions.get(order=1)
        q2 = self.quiz.questions.get(order=2)
        correct_q1 = q1.answers.get(is_correct=True)
        correct_q2 = q2.answers.get(is_correct=True)

        response = client.post(
            f'/api/quizzes/{self.quiz.id}/submit/',
            {
                'answers': [
                    {'question_id': q1.id, 'answer_id': correct_q1.id},
                    {'question_id': q2.id, 'answer_id': correct_q2.id},
                ]
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn('score', response.data)
        self.assertIn('passed', response.data)
        self.assertEqual(response.data['score'], '100.00')
        self.assertTrue(response.data['passed'])

    def test_unauthenticated_cannot_submit(self):
        """Un visiteur non connecté ne peut pas soumettre un quiz."""
        q1 = self.quiz.questions.get(order=1)
        response = self.client.post(
            f'/api/quizzes/{self.quiz.id}/submit/',
            {'answers': [{'question_id': q1.id, 'answer_id': 1}]},
            format='json',
        )
        self.assertEqual(response.status_code, 401)

    def test_submit_wrong_answers(self):
        """Soumettre toutes les mauvaises réponses → score 0%, non validé."""
        client = get_auth_client(self.apprenant)
        q1 = self.quiz.questions.get(order=1)
        q2 = self.quiz.questions.get(order=2)
        wrong_q1 = q1.answers.filter(is_correct=False).first()
        wrong_q2 = q2.answers.get(is_correct=False)

        response = client.post(
            f'/api/quizzes/{self.quiz.id}/submit/',
            {
                'answers': [
                    {'question_id': q1.id, 'answer_id': wrong_q1.id},
                    {'question_id': q2.id, 'answer_id': wrong_q2.id},
                ]
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['score'], '0.00')
        self.assertFalse(response.data['passed'])


# ═══════════════════════════════════════════════
# TESTS DE L'HISTORIQUE
# ═══════════════════════════════════════════════

class QuizHistoryTest(APITestCase):
    """Tests de l'historique des tentatives."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Jean', last_name='Formateur',
            role=User.Role.FORMATEUR,
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Marie', last_name='Apprenant',
        )
        self.autre_apprenant = User.objects.create_user(
            email='autre@test.com', password='Pass123!',
            first_name='Bob', last_name='Autre',
        )
        self.formation = Formation.objects.create(
            formateur=self.formateur, titre='Formation', description='...'
        )
        self.module = Module.objects.create(
            formation=self.formation, titre='Module 1', order=1
        )
        self.quiz = create_quiz_with_questions(self.module)

        # Crée 2 tentatives pour l'apprenant
        for score_val in [Decimal('50.00'), Decimal('80.00')]:
            QuizAttempt.objects.create(
                user=self.apprenant,
                quiz=self.quiz,
                score=score_val,
                earned_points=1 if score_val == 50 else 2,
                total_points=2,
                passed=score_val >= 70,
            )

        # Crée 1 tentative pour l'autre apprenant (ne doit pas apparaître)
        QuizAttempt.objects.create(
            user=self.autre_apprenant,
            quiz=self.quiz,
            score=Decimal('100.00'),
            earned_points=2,
            total_points=2,
            passed=True,
        )

    def test_history_shows_only_own_attempts(self):
        """L'historique ne montre que les tentatives de l'utilisateur connecté."""
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/quizzes/{self.quiz.id}/history/')
        self.assertEqual(response.status_code, 200)
        # response.data est paginé : {'count': N, 'results': [...]}
        # L'apprenant a 2 tentatives (pas les 3 au total)
        self.assertEqual(response.data['count'], 2)

    def test_history_unauthenticated(self):
        """Un visiteur non connecté ne peut pas voir l'historique."""
        response = self.client.get(f'/api/quizzes/{self.quiz.id}/history/')
        self.assertEqual(response.status_code, 401)

    def test_history_contains_score_and_passed(self):
        """L'historique contient le score et si le quiz était validé."""
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/quizzes/{self.quiz.id}/history/')
        self.assertEqual(response.status_code, 200)
        # Les tentatives sont dans response.data['results'] (liste paginée)
        for attempt in response.data['results']:
            self.assertIn('score', attempt)
            self.assertIn('passed', attempt)
            self.assertIn('completed_at', attempt)
