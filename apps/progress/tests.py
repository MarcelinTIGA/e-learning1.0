"""
Tests pour l'app 'progress'.

Organisation :
    - ProgressServiceTest       : logique métier (calcul %, marquer leçon, position vidéo)
    - ProgressSignalTest        : signal QuizAttempt → recalcul progression
    - ProgressAPITest           : endpoints REST (formations, leçons)
    - ResumeTest                : fonctionnalité "reprendre où j'en étais"

Total : ~22 tests
"""

from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import TestCase

from apps.courses.models import Category, Formation, Lesson, Module
from apps.quizzes.models import Answer, Question, Quiz, QuizAttempt
from apps.users.models import User

from .models import FormationProgress, LessonProgress
from .services import ProgressService


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_auth_client(user):
    """Client API authentifié avec JWT."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


def create_formation_with_content(formateur, nb_modules=2, lessons_per_module=2, with_quiz=True):
    """
    Crée une formation complète avec modules, leçons et quiz pour les tests.

    Args:
        formateur:          Propriétaire de la formation
        nb_modules:         Nombre de modules à créer
        lessons_per_module: Nombre de leçons par module
        with_quiz:          Si True, ajoute un quiz à chaque module

    Returns:
        dict avec 'formation', 'modules', 'lessons', 'quizzes'
    """
    category, _ = Category.objects.get_or_create(name='Prog Cat', defaults={'slug': 'prog-cat'})

    formation = Formation.objects.create(
        formateur=formateur,
        categorie=category,
        titre='Formation Test Progress',
        description='Test',
        prix=Decimal('0'),
        niveau=Formation.Level.DEBUTANT,
        is_published=True,
    )

    modules = []
    lessons = []
    quizzes = []

    for m_idx in range(nb_modules):
        module = Module.objects.create(
            formation=formation,
            titre=f'Module {m_idx + 1}',
            order=m_idx + 1,
        )
        modules.append(module)

        for l_idx in range(lessons_per_module):
            lesson = Lesson.objects.create(
                module=module,
                titre=f'Leçon {l_idx + 1} du Module {m_idx + 1}',
                content_type=Lesson.ContentType.TEXT,
                text_content='Contenu texte de test.',
                order=l_idx + 1,
            )
            lessons.append(lesson)

        if with_quiz:
            quiz = Quiz.objects.create(
                module=module,
                titre=f'Quiz Module {m_idx + 1}',
                passing_score=70,
            )
            # Ajouter une question avec une bonne réponse
            question = Question.objects.create(
                quiz=quiz,
                text='Question test ?',
                question_type=Question.QuestionType.QCM,
                order=1,
                points=1,
            )
            Answer.objects.create(question=question, text='Bonne réponse', is_correct=True)
            Answer.objects.create(question=question, text='Mauvaise réponse', is_correct=False)
            quizzes.append(quiz)

    return {
        'formation': formation,
        'modules':   modules,
        'lessons':   lessons,
        'quizzes':   quizzes,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TESTS DU SERVICE MÉTIER
# ─────────────────────────────────────────────────────────────────────────────

class ProgressServiceTest(TestCase):
    """Teste la logique du ProgressService sans passer par HTTP."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='form@prog.com', password='pass', role=User.Role.FORMATEUR
        )
        self.apprenant = User.objects.create_user(
            email='app@prog.com', password='pass', role=User.Role.APPRENANT
        )
        # Formation avec 2 modules, 2 leçons chacun, 2 quiz → 4 leçons + 2 quiz = 6 items
        self.content = create_formation_with_content(
            self.formateur, nb_modules=2, lessons_per_module=2, with_quiz=True
        )
        self.formation = self.content['formation']
        self.lessons   = self.content['lessons']
        self.quizzes   = self.content['quizzes']

    def test_recalcul_progression_zero_au_depart(self):
        """
        Au départ, sans rien faire, la progression doit être 0%.
        """
        progress = ProgressService.recalculate_formation_progress(
            self.apprenant, self.formation
        )

        self.assertEqual(progress.percentage, Decimal('0.00'))
        self.assertFalse(progress.is_completed)
        self.assertEqual(progress.completed_lessons, 0)
        self.assertEqual(progress.total_lessons, 4)     # 2 modules × 2 leçons
        self.assertEqual(progress.total_quizzes, 2)     # 2 modules × 1 quiz

    def test_marquer_une_lecon_terminee(self):
        """
        Marquer 1 leçon sur 4 → progression = 1/(4+2) = 16.67%
        """
        ProgressService.mark_lesson_complete(self.apprenant, self.lessons[0].pk)

        progress = FormationProgress.objects.get(
            user=self.apprenant, formation=self.formation
        )

        # 1 leçon terminée / (4 leçons + 2 quiz) = 16.67%
        self.assertEqual(progress.completed_lessons, 1)
        expected_pct = (Decimal('1') / Decimal('6') * Decimal('100')).quantize(Decimal('0.01'))
        self.assertEqual(progress.percentage, expected_pct)
        self.assertFalse(progress.is_completed)

    def test_toutes_lecons_mais_pas_quiz(self):
        """
        Terminer toutes les leçons sans valider les quiz → pas is_completed.
        4 leçons / 6 items = 66.67%
        """
        for lesson in self.lessons:
            ProgressService.mark_lesson_complete(self.apprenant, lesson.pk)

        progress = FormationProgress.objects.get(
            user=self.apprenant, formation=self.formation
        )

        self.assertEqual(progress.completed_lessons, 4)
        self.assertEqual(progress.passed_quizzes, 0)
        self.assertFalse(progress.is_completed)  # Pas encore 100%

    def test_progression_complete_100_pourcent(self):
        """
        Terminer toutes les leçons ET valider tous les quiz → is_completed=True, 100%.
        """
        # Terminer toutes les leçons
        for lesson in self.lessons:
            ProgressService.mark_lesson_complete(self.apprenant, lesson.pk)

        # Valider tous les quiz (créer des QuizAttempt avec passed=True)
        for quiz in self.quizzes:
            QuizAttempt.objects.create(
                user=self.apprenant,
                quiz=quiz,
                score=Decimal('100.00'),
                earned_points=1,
                total_points=1,
                passed=True,
            )

        # Recalculer (les QuizAttempt ne déclenchent pas le signal dans les tests unitaires)
        progress = ProgressService.recalculate_formation_progress(
            self.apprenant, self.formation
        )

        self.assertEqual(progress.percentage, Decimal('100.00'))
        self.assertTrue(progress.is_completed)

    def test_sauvegarde_position_video(self):
        """
        Sauvegarder la position dans une vidéo doit mettre à jour video_position_seconds.
        """
        lesson = self.lessons[0]

        ProgressService.save_video_position(self.apprenant, lesson.pk, 245)

        lp = LessonProgress.objects.get(user=self.apprenant, lesson=lesson)
        self.assertEqual(lp.video_position_seconds, 245)
        # Sauvegarder la position ne marque PAS la leçon comme terminée
        self.assertFalse(lp.completed)

    def test_reprise_video_mise_a_jour(self):
        """
        Appeler save_video_position deux fois doit mettre à jour la position.
        """
        lesson = self.lessons[0]

        ProgressService.save_video_position(self.apprenant, lesson.pk, 100)
        ProgressService.save_video_position(self.apprenant, lesson.pk, 350)

        lp = LessonProgress.objects.get(user=self.apprenant, lesson=lesson)
        self.assertEqual(lp.video_position_seconds, 350)

    def test_marquer_lecon_deja_terminee_ne_recalcule_pas(self):
        """
        Marquer une leçon déjà terminée ne doit pas créer de doublon
        ni recalculer inutilement.
        """
        lesson = self.lessons[0]

        ProgressService.mark_lesson_complete(self.apprenant, lesson.pk)
        ProgressService.mark_lesson_complete(self.apprenant, lesson.pk)  # 2ème appel

        # Un seul LessonProgress doit exister
        count = LessonProgress.objects.filter(user=self.apprenant, lesson=lesson).count()
        self.assertEqual(count, 1)

    def test_update_last_accessed(self):
        """
        Mettre à jour la dernière leçon accédée doit modifier FormationProgress.last_accessed_lesson.
        """
        lesson = self.lessons[1]

        ProgressService.update_last_accessed(self.apprenant, lesson.pk)

        fp = FormationProgress.objects.get(user=self.apprenant, formation=self.formation)
        self.assertEqual(fp.last_accessed_lesson, lesson)


# ─────────────────────────────────────────────────────────────────────────────
# TESTS DES SIGNAUX
# ─────────────────────────────────────────────────────────────────────────────

class ProgressSignalTest(TestCase):
    """
    Teste que le signal post_save sur QuizAttempt déclenche le recalcul.
    """

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='form2@prog.com', password='pass', role=User.Role.FORMATEUR
        )
        self.apprenant = User.objects.create_user(
            email='app2@prog.com', password='pass', role=User.Role.APPRENANT
        )
        self.content = create_formation_with_content(
            self.formateur, nb_modules=1, lessons_per_module=2, with_quiz=True
        )
        self.formation = self.content['formation']
        self.quiz = self.content['quizzes'][0]

    def test_signal_quiz_validé_recalcule_progression(self):
        """
        Créer un QuizAttempt(passed=True) via save() doit déclencher le signal
        et recalculer automatiquement FormationProgress.
        """
        # Le signal est connecté dans apps.py via ready()
        # Dans les tests Django, ready() est appelé → le signal est actif

        QuizAttempt.objects.create(
            user=self.apprenant,
            quiz=self.quiz,
            score=Decimal('100.00'),
            earned_points=1,
            total_points=1,
            passed=True,
        )

        # FormationProgress doit avoir été créé/mis à jour par le signal
        fp = FormationProgress.objects.filter(
            user=self.apprenant, formation=self.formation
        ).first()

        self.assertIsNotNone(fp)
        self.assertEqual(fp.passed_quizzes, 1)

    def test_signal_quiz_echoué_recalcule_aussi(self):
        """
        Un quiz échoué doit aussi déclencher le recalcul (passed_quizzes = 0).
        """
        QuizAttempt.objects.create(
            user=self.apprenant,
            quiz=self.quiz,
            score=Decimal('30.00'),
            earned_points=0,
            total_points=1,
            passed=False,
        )

        fp = FormationProgress.objects.filter(
            user=self.apprenant, formation=self.formation
        ).first()

        self.assertIsNotNone(fp)
        self.assertEqual(fp.passed_quizzes, 0)  # Non validé


# ─────────────────────────────────────────────────────────────────────────────
# TESTS DES ENDPOINTS API
# ─────────────────────────────────────────────────────────────────────────────

class ProgressAPITest(TestCase):
    """Teste les endpoints /api/progress/."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='form3@prog.com', password='pass', role=User.Role.FORMATEUR
        )
        self.apprenant = User.objects.create_user(
            email='app3@prog.com', password='pass', role=User.Role.APPRENANT
        )
        self.content = create_formation_with_content(
            self.formateur, nb_modules=2, lessons_per_module=2, with_quiz=False
        )
        self.formation = self.content['formation']
        self.lessons   = self.content['lessons']

    def test_non_authentifie_bloque(self):
        """Tous les endpoints progress nécessitent une authentification."""
        client = APIClient()
        url = reverse('progress:formation-progress-list')
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_liste_progressions_vide_au_depart(self):
        """
        GET /api/progress/formations/ → liste vide si l'apprenant n'a rien commencé.
        """
        client = get_auth_client(self.apprenant)
        url = reverse('progress:formation-progress-list')
        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_marquer_lecon_terminee_via_api(self):
        """
        POST /api/progress/lessons/<id>/complete/ → leçon marquée + progression recalculée.
        """
        client = get_auth_client(self.apprenant)
        lesson = self.lessons[0]
        url = reverse('progress:lesson-complete', kwargs={'lesson_id': lesson.pk})

        response = client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # La réponse doit confirmer que la leçon est terminée
        self.assertTrue(response.data['completed'])

    def test_sauvegarder_position_video_via_api(self):
        """
        POST /api/progress/lessons/<id>/video/ → position sauvegardée.
        """
        client = get_auth_client(self.apprenant)
        lesson = self.lessons[0]
        url = reverse('progress:lesson-video-position', kwargs={'lesson_id': lesson.pk})

        response = client.post(url, {'position_seconds': 180}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['video_position_seconds'], 180)

    def test_position_video_negative_invalide(self):
        """
        position_seconds < 0 doit retourner une erreur de validation (400).
        """
        client = get_auth_client(self.apprenant)
        lesson = self.lessons[0]
        url = reverse('progress:lesson-video-position', kwargs={'lesson_id': lesson.pk})

        response = client.post(url, {'position_seconds': -10}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_detail_progression_formation(self):
        """
        GET /api/progress/formations/<id>/ → retourne la progression (créée si inexistante).
        """
        client = get_auth_client(self.apprenant)
        url = reverse('progress:formation-progress-detail', kwargs={'formation_id': self.formation.pk})

        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(response.data['percentage'])), Decimal('0.00'))

    def test_progression_apparait_apres_lecon_terminee(self):
        """
        Après avoir marqué une leçon terminée, la progression doit apparaître dans la liste.
        """
        # Marquer une leçon via le service
        ProgressService.mark_lesson_complete(self.apprenant, self.lessons[0].pk)

        client = get_auth_client(self.apprenant)
        url = reverse('progress:formation-progress-list')
        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_detail_lecon_cree_progression_si_absente(self):
        """
        GET /api/progress/lessons/<id>/ → crée LessonProgress si absent, retourne les données.
        """
        client = get_auth_client(self.apprenant)
        lesson = self.lessons[0]
        url = reverse('progress:lesson-progress-detail', kwargs={'lesson_id': lesson.pk})

        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # La leçon n'est pas encore terminée
        self.assertFalse(response.data['completed'])
        # La position vidéo est à 0
        self.assertEqual(response.data['video_position_seconds'], 0)


# ─────────────────────────────────────────────────────────────────────────────
# TESTS REPRISE DE COURS
# ─────────────────────────────────────────────────────────────────────────────

class ResumeTest(TestCase):
    """Teste la fonctionnalité 'reprendre où j'en étais'."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='form4@prog.com', password='pass', role=User.Role.FORMATEUR
        )
        self.apprenant = User.objects.create_user(
            email='app4@prog.com', password='pass', role=User.Role.APPRENANT
        )
        self.content = create_formation_with_content(
            self.formateur, nb_modules=1, lessons_per_module=3, with_quiz=False
        )
        self.formation = self.content['formation']
        self.lessons   = self.content['lessons']

    def test_resume_sans_historique(self):
        """
        Si l'apprenant n'a accédé à aucune leçon, le resume retourne lesson_id=None.
        """
        client = get_auth_client(self.apprenant)
        url = reverse('progress:formation-resume', kwargs={'formation_id': self.formation.pk})

        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['lesson_id'])

    def test_resume_apres_acces_lecon(self):
        """
        Après avoir accédé à la leçon 2, le resume doit retourner lesson_id=leçon 2.
        """
        # Simuler un accès à la leçon 2
        ProgressService.update_last_accessed(self.apprenant, self.lessons[1].pk)

        client = get_auth_client(self.apprenant)
        url = reverse('progress:formation-resume', kwargs={'formation_id': self.formation.pk})

        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lesson_id'], self.lessons[1].pk)

    def test_resume_se_met_a_jour(self):
        """
        Accéder à une nouvelle leçon met à jour le point de reprise.
        """
        # Accéder à leçon 1, puis leçon 3
        ProgressService.update_last_accessed(self.apprenant, self.lessons[0].pk)
        ProgressService.update_last_accessed(self.apprenant, self.lessons[2].pk)

        fp = FormationProgress.objects.get(user=self.apprenant, formation=self.formation)
        # La dernière leçon accédée doit être la leçon 3 (index 2)
        self.assertEqual(fp.last_accessed_lesson, self.lessons[2])
