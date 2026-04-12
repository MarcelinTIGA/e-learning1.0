"""
Tests pour l'app 'progress'.

Organisation :
  - LessonProgressTest     : Marquer une leçon terminée, position vidéo
  - FormationProgressTest  : Progression globale, recalcul
  - LessonProgressDetail   : État d'une leçon, reprise
  - ResumeFormationTest    : Reprendre où on en était
"""

from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Category, Formation, Lesson, Module
from apps.users.models import User

from .models import FormationProgress, LessonProgress


def get_auth_client(user):
    """Crée un APIClient authentifié avec JWT."""
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


class LessonProgressTest(APITestCase):
    """Tests de progression par leçon."""

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
        self.categorie = Category.objects.create(name='Python')
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            categorie=self.categorie,
            titre='Python pour débutants',
            description='...',
            is_published=True,
        )
        self.module = Module.objects.create(
            formation=self.formation,
            titre='Module 1',
            order=1,
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            titre='Leçon 1 : Introduction',
            content_type=Lesson.ContentType.TEXT,
            text_content='Bonjour',
            order=1,
            duration_minutes=10,
        )
        self.lesson2 = Lesson.objects.create(
            module=self.module,
            titre='Leçon 2 : Variables',
            content_type=Lesson.ContentType.VIDEO,
            video_url='https://youtube.com/watch?v=test',
            order=2,
            duration_minutes=15,
        )

    def test_mark_lesson_complete(self):
        """Marquer une leçon comme terminée."""
        client = get_auth_client(self.apprenant)
        response = client.post(f'/api/progress/lessons/{self.lesson.pk}/complete/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(LessonProgress.objects.filter(
            user=self.apprenant,
            lesson=self.lesson,
            completed=True,
        ).exists())

    def test_mark_complete_creates_progress(self):
        """Marquer une leçon crée la progression formation si elle n'existe pas."""
        client = get_auth_client(self.apprenant)
        client.post(f'/api/progress/lessons/{self.lesson.pk}/complete/')

        # La progression formation doit être créée
        self.assertTrue(FormationProgress.objects.filter(
            user=self.apprenant,
            formation=self.formation,
        ).exists())

    def test_mark_lesson_not_found(self):
        """Marquer une leçon inexistante → erreur 400."""
        client = get_auth_client(self.apprenant)
        response = client.post('/api/progress/lessons/99999/complete/')
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_cannot_complete(self):
        """Un utilisateur non authentifié ne peut pas marquer une leçon."""
        response = self.client.post(f'/api/progress/lessons/{self.lesson.pk}/complete/')
        self.assertEqual(response.status_code, 401)

    def test_save_video_position(self):
        """Sauvegarder la position dans une vidéo."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            f'/api/progress/lessons/{self.lesson2.pk}/video/',
            {'position_seconds': 245},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        progress = LessonProgress.objects.get(
            user=self.apprenant,
            lesson=self.lesson2,
        )
        self.assertEqual(progress.video_position_seconds, 245)

    def test_save_video_position_negative(self):
        """Position négative → erreur de validation."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            f'/api/progress/lessons/{self.lesson2.pk}/video/',
            {'position_seconds': -10},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_save_video_position_not_found(self):
        """Sauvegarder sur une leçon inexistante → erreur."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            '/api/progress/lessons/99999/video/',
            {'position_seconds': 100},
            format='json',
        )
        self.assertEqual(response.status_code, 400)


class FormationProgressTest(APITestCase):
    """Tests de progression globale par formation."""

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
        self.categorie = Category.objects.create(name='Python')
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            categorie=self.categorie,
            titre='Python pour débutants',
            description='...',
            is_published=True,
        )
        # 3 leçons
        self.module = Module.objects.create(
            formation=self.formation,
            titre='Module 1',
            order=1,
        )
        for i in range(3):
            Lesson.objects.create(
                module=self.module,
                titre=f'Leçon {i+1}',
                content_type=Lesson.ContentType.TEXT,
                text_content=f'Contenu {i+1}',
                order=i+1,
                duration_minutes=10,
            )

    def test_list_progressions(self):
        """L'apprenant voit ses progressions."""
        # Créer une progression
        FormationProgress.objects.create(
            user=self.apprenant,
            formation=self.formation,
            percentage=33.33,
            completed_lessons=1,
            total_lessons=3,
        )

        client = get_auth_client(self.apprenant)
        response = client.get('/api/progress/formations/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_progression_detail_creates(self):
        """Accéder à la progression d'une formation la crée si elle n'existe pas."""
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/progress/formations/{self.formation.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(FormationProgress.objects.filter(
            user=self.apprenant,
            formation=self.formation,
        ).exists())

    def test_recalculate_on_lesson_complete(self):
        """Compléter toutes les leçons → progression = 100%."""
        client = get_auth_client(self.apprenant)
        lessons = Lesson.objects.filter(module__formation=self.formation)

        for lesson in lessons:
            client.post(f'/api/progress/lessons/{lesson.pk}/complete/')

        progress = FormationProgress.objects.get(
            user=self.apprenant,
            formation=self.formation,
        )
        self.assertEqual(progress.completed_lessons, 3)
        self.assertEqual(progress.total_lessons, 3)
        # Pas de quiz → 3/3 = 100%
        self.assertEqual(float(progress.percentage), 100.0)
        self.assertTrue(progress.is_completed)

    def test_partial_progress(self):
        """Progression partielle après 1 leçon sur 3."""
        client = get_auth_client(self.apprenant)
        first_lesson = Lesson.objects.filter(module__formation=self.formation).first()
        client.post(f'/api/progress/lessons/{first_lesson.pk}/complete/')

        progress = FormationProgress.objects.get(
            user=self.apprenant,
            formation=self.formation,
        )
        self.assertEqual(progress.completed_lessons, 1)
        self.assertEqual(progress.total_lessons, 3)
        # 1/3 = 33.33%
        self.assertAlmostEqual(float(progress.percentage), 33.33, places=1)


class LessonProgressDetailTest(APITestCase):
    """Tests du détail de progression d'une leçon."""

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
        self.lesson = Lesson.objects.create(
            module=self.module,
            titre='Leçon 1',
            content_type=Lesson.ContentType.TEXT,
            text_content='Contenu',
            order=1,
        )

    def test_get_lesson_progress_new(self):
        """Obtenir la progression d'une leçon jamais accédée → créée."""
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/progress/lessons/{self.lesson.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['completed'])
        self.assertEqual(response.data['video_position_seconds'], 0)

    def test_get_lesson_progress_existing(self):
        """Obtenir la progression d'une leçon déjà accédée."""
        LessonProgress.objects.create(
            user=self.apprenant,
            lesson=self.lesson,
            completed=True,
            video_position_seconds=120,
        )
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/progress/lessons/{self.lesson.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['completed'])
        self.assertEqual(response.data['video_position_seconds'], 120)

    def test_get_lesson_progress_not_found(self):
        """Leçon inexistante → 404."""
        client = get_auth_client(self.apprenant)
        response = client.get('/api/progress/lessons/99999/')
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_cannot_access(self):
        """Un utilisateur non authentifié ne peut pas accéder."""
        response = self.client.get(f'/api/progress/lessons/{self.lesson.pk}/')
        self.assertEqual(response.status_code, 401)


class ResumeFormationTest(APITestCase):
    """Tests de reprise de formation."""

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
        self.lesson = Lesson.objects.create(
            module=self.module,
            titre='Leçon 1',
            content_type=Lesson.ContentType.TEXT,
            text_content='Contenu',
            order=1,
        )

    def test_resume_not_started(self):
        """Reprendre une formation jamais commencée → lesson_id = None."""
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/progress/formations/{self.formation.pk}/resume/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['lesson_id'])

    def test_resume_with_progress(self):
        """Reprendre une formation commencée → retourne la dernière leçon."""
        progress = FormationProgress.objects.create(
            user=self.apprenant,
            formation=self.formation,
            last_accessed_lesson=self.lesson,
        )
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/progress/formations/{self.formation.pk}/resume/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lesson_id'], self.lesson.pk)
        self.assertEqual(response.data['lesson_titre'], self.lesson.titre)

    def test_resume_not_found(self):
        """Reprendre une formation inexistante → 200 avec None (pas d'erreur)."""
        client = get_auth_client(self.apprenant)
        response = client.get('/api/progress/formations/99999/resume/')
        # La vue utilise get_or_create, donc ça crée une nouvelle progression vide
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['lesson_id'])
