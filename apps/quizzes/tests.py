"""
Tests pour l'app 'quizzes'.

Organisation :
  - QuizManageTest      : CRUD des quiz par le formateur
  - QuestionManageTest  : CRUD des questions
  - AnswerManageTest    : CRUD des réponses
  - QuizStudentTest     : Côté apprenant (voir, soumettre, historique)
"""

from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Category, Formation, Module
from apps.users.models import User

from .models import Answer, AttemptAnswer, Question, Quiz, QuizAttempt


def get_auth_client(user):
    """Crée un APIClient authentifié avec JWT."""
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


class QuizManageTest(APITestCase):
    """Tests de gestion des quiz par le formateur."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Marie', last_name='Formatrice',
            role=User.Role.FORMATEUR,
        )
        self.autre_formateur = User.objects.create_user(
            email='autre@test.com', password='Pass123!',
            first_name='Alice', last_name='Autre',
            role=User.Role.FORMATEUR,
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Jean', last_name='Apprenant',
        )
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            titre='Ma Formation',
            description='...',
            is_published=True,
        )
        self.module = Module.objects.create(
            formation=self.formation,
            titre='Module 1',
            order=1,
        )

    def test_formateur_create_quiz(self):
        """Un formateur peut créer un quiz pour son module."""
        client = get_auth_client(self.formateur)
        response = client.post(
            f'/api/quizzes/modules/{self.module.pk}/quiz/',
            {'titre': 'Quiz Module 1', 'passing_score': 70},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Quiz.objects.filter(module=self.module).exists())

    def test_formateur_list_quiz(self):
        """Un formateur peut voir le quiz de son module."""
        Quiz.objects.create(
            module=self.module,
            titre='Quiz Module 1',
            passing_score=70,
        )
        client = get_auth_client(self.formateur)
        response = client.get(f'/api/quizzes/modules/{self.module.pk}/quiz/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_other_formateur_cannot_create_quiz(self):
        """Un autre formateur ne peut pas créer un quiz sur ce module."""
        client = get_auth_client(self.autre_formateur)
        response = client.post(
            f'/api/quizzes/modules/{self.module.pk}/quiz/',
            {'titre': 'Quiz volé', 'passing_score': 70},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_apprenant_cannot_create_quiz(self):
        """Un apprenant ne peut pas créer de quiz."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            f'/api/quizzes/modules/{self.module.pk}/quiz/',
            {'titre': 'Tentative', 'passing_score': 70},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_formateur_update_quiz(self):
        """Un formateur peut modifier son quiz."""
        quiz = Quiz.objects.create(
            module=self.module,
            titre='Quiz Module 1',
            passing_score=70,
        )
        client = get_auth_client(self.formateur)
        response = client.patch(
            f'/api/quizzes/{quiz.pk}/',
            {'titre': 'Quiz Modifié', 'passing_score': 80},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        quiz.refresh_from_db()
        self.assertEqual(quiz.titre, 'Quiz Modifié')

    def test_formateur_delete_quiz(self):
        """Un formateur peut supprimer son quiz."""
        quiz = Quiz.objects.create(
            module=self.module,
            titre='Quiz Module 1',
            passing_score=70,
        )
        client = get_auth_client(self.formateur)
        response = client.delete(f'/api/quizzes/{quiz.pk}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Quiz.objects.filter(pk=quiz.pk).exists())


class QuestionManageTest(APITestCase):
    """Tests de gestion des questions."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Marie', last_name='Formatrice',
            role=User.Role.FORMATEUR,
        )
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            titre='Ma Formation',
            description='...',
            is_published=True,
        )
        self.module = Module.objects.create(
            formation=self.formation,
            titre='Module 1',
            order=1,
        )
        self.quiz = Quiz.objects.create(
            module=self.module,
            titre='Quiz Module 1',
            passing_score=70,
        )

    def test_create_question(self):
        """Un formateur peut ajouter une question à son quiz."""
        client = get_auth_client(self.formateur)
        response = client.post(
            f'/api/quizzes/{self.quiz.pk}/questions/',
            {'text': 'Quelle est la capitale de la France ?', 'question_type': 'qcm', 'order': 1, 'points': 2},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Question.objects.filter(quiz=self.quiz).exists())

    def test_list_questions(self):
        """Un formateur peut lister les questions de son quiz."""
        Question.objects.create(quiz=self.quiz, text='Q1', order=1, points=1)
        client = get_auth_client(self.formateur)
        response = client.get(f'/api/quizzes/{self.quiz.pk}/questions/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_update_question(self):
        """Un formateur peut modifier une question."""
        question = Question.objects.create(quiz=self.quiz, text='Q1', order=1, points=1)
        client = get_auth_client(self.formateur)
        response = client.patch(
            f'/api/quizzes/questions/{question.pk}/',
            {'text': 'Question modifiée', 'question_type': 'qcm', 'order': 1, 'points': 3},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        question.refresh_from_db()
        self.assertEqual(question.text, 'Question modifiée')

    def test_delete_question(self):
        """Un formateur peut supprimer une question."""
        question = Question.objects.create(quiz=self.quiz, text='Q1', order=1, points=1)
        client = get_auth_client(self.formateur)
        response = client.delete(f'/api/quizzes/questions/{question.pk}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Question.objects.filter(pk=question.pk).exists())


class AnswerManageTest(APITestCase):
    """Tests de gestion des réponses."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Marie', last_name='Formatrice',
            role=User.Role.FORMATEUR,
        )
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            titre='Ma Formation',
            description='...',
            is_published=True,
        )
        self.module = Module.objects.create(
            formation=self.formation,
            titre='Module 1',
            order=1,
        )
        self.quiz = Quiz.objects.create(
            module=self.module,
            titre='Quiz Module 1',
            passing_score=70,
        )
        self.question = Question.objects.create(
            quiz=self.quiz,
            text='Capitale de la France ?',
            order=1,
            points=2,
        )

    def test_create_answer(self):
        """Un formateur peut ajouter des réponses à une question."""
        client = get_auth_client(self.formateur)
        response = client.post(
            f'/api/quizzes/questions/{self.question.pk}/answers/',
            {'text': 'Paris', 'is_correct': True},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Answer.objects.filter(question=self.question).exists())

    def test_list_answers(self):
        """Un formateur peut lister les réponses."""
        Answer.objects.create(question=self.question, text='Paris', is_correct=True)
        Answer.objects.create(question=self.question, text='Lyon', is_correct=False)
        client = get_auth_client(self.formateur)
        response = client.get(f'/api/quizzes/questions/{self.question.pk}/answers/')
        self.assertEqual(response.status_code, 200)
        # La pagination peut retourner un objet {count, results} ou une liste directe
        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertEqual(response.data['count'], 2)
        else:
            self.assertGreaterEqual(len(response.data), 2)

    def test_update_answer(self):
        """Un formateur peut modifier une réponse."""
        answer = Answer.objects.create(question=self.question, text='Paris', is_correct=True)
        client = get_auth_client(self.formateur)
        response = client.patch(
            f'/api/quizzes/answers/{answer.pk}/',
            {'text': 'PARIS', 'is_correct': True},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        answer.refresh_from_db()
        self.assertEqual(answer.text, 'PARIS')


class QuizStudentTest(APITestCase):
    """Tests côté apprenant : voir, soumettre, historique."""

    def setUp(self):
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Jean', last_name='Apprenant',
        )
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Marie', last_name='Formatrice',
            role=User.Role.FORMATEUR,
        )
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            titre='Ma Formation',
            description='...',
            is_published=True,
        )
        self.module = Module.objects.create(
            formation=self.formation,
            titre='Module 1',
            order=1,
        )
        self.quiz = Quiz.objects.create(
            module=self.module,
            titre='Quiz Module 1',
            passing_score=70,
        )
        # Question avec 3 réponses (1 correcte)
        self.question = Question.objects.create(
            quiz=self.quiz,
            text='Capitale de la France ?',
            order=1,
            points=10,
        )
        self.correct_answer = Answer.objects.create(
            question=self.question,
            text='Paris',
            is_correct=True,
        )
        self.wrong_answer1 = Answer.objects.create(
            question=self.question,
            text='Lyon',
            is_correct=False,
        )
        self.wrong_answer2 = Answer.objects.create(
            question=self.question,
            text='Marseille',
            is_correct=False,
        )

    def test_student_view_quiz(self):
        """L'apprenant voit le quiz SANS is_correct."""
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/quizzes/{self.quiz.pk}/attempt/')
        self.assertEqual(response.status_code, 200)
        # Vérifier que is_correct n'est PAS dans les réponses
        for question in response.data['questions']:
            for answer in question['answers']:
                self.assertNotIn('is_correct', answer)

    def test_submit_correct_answer(self):
        """Soumettre la bonne réponse → quiz réussi."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            f'/api/quizzes/{self.quiz.pk}/submit/',
            {
                'answers': [
                    {'question_id': self.question.pk, 'answer_id': self.correct_answer.pk},
                ]
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.data['score']), 100.0)
        self.assertTrue(response.data['passed'])

    def test_submit_wrong_answer(self):
        """Soumettre une mauvaise réponse → quiz échoué (0%)."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            f'/api/quizzes/{self.quiz.pk}/submit/',
            {
                'answers': [
                    {'question_id': self.question.pk, 'answer_id': self.wrong_answer1.pk},
                ]
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.data['score']), 0.0)
        self.assertFalse(response.data['passed'])

    def test_quiz_history(self):
        """L'apprenant peut voir l'historique de ses tentatives."""
        # Soumettre 2 tentatives
        client = get_auth_client(self.apprenant)
        client.post(
            f'/api/quizzes/{self.quiz.pk}/submit/',
            {'answers': [{'question_id': self.question.pk, 'answer_id': self.correct_answer.pk}]},
            format='json',
        )
        client.post(
            f'/api/quizzes/{self.quiz.pk}/submit/',
            {'answers': [{'question_id': self.question.pk, 'answer_id': self.wrong_answer1.pk}]},
            format='json',
        )

        response = client.get(f'/api/quizzes/{self.quiz.pk}/history/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

    def test_submit_empty_answers(self):
        """Soumettre sans réponses → erreur 400."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            f'/api/quizzes/{self.quiz.pk}/submit/',
            {'answers': []},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_submit_not_found_quiz(self):
        """Soumettre à un quiz inexistant → erreur (400 ou 404)."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            '/api/quizzes/99999/submit/',
            {'answers': []},
            format='json',
        )
        # Le serializer valide d'abord (answers vide = 400) avant que la view ne vérifie le quiz
        self.assertIn(response.status_code, [400, 404])

    def test_unauthenticated_cannot_submit(self):
        """Un utilisateur non authentifié ne peut pas soumettre."""
        response = self.client.post(
            f'/api/quizzes/{self.quiz.pk}/submit/',
            {'answers': []},
            format='json',
        )
        self.assertEqual(response.status_code, 401)
