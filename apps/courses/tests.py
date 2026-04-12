"""
Tests pour l'app 'courses'.

Organisation :
  - CategoryTest         : CRUD des catégories (accès public + admin)
  - CatalogueTest        : Catalogue public (filtres, recherche, visibilité)
  - FormationManageTest  : Gestion des formations par le formateur
  - ModuleTest           : Gestion des modules
  - LessonTest           : Gestion des leçons

Conventions :
  - setUp() : crée les données de test avant chaque test
  - Chaque test est indépendant (la BDD est réinitialisée entre chaque test)
"""

from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User

from .models import Category, Formation, Lesson, Module


def get_auth_client(user):
    """
    Fonction utilitaire : crée un APIClient authentifié avec le token JWT de l'utilisateur.
    Évite de répéter le code de création du token dans chaque test.
    """
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


class CategoryTest(APITestCase):
    """Tests des endpoints de catégories."""

    def setUp(self):
        # Création d'un administrateur pour les tests qui nécessitent des droits admin
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Pass123!',
            first_name='Admin', last_name='Test',
            role=User.Role.ADMINISTRATEUR,
        )
        # Une catégorie existante pour les tests de lecture/modification
        self.category = Category.objects.create(name='Informatique', description='Cours info')

    def test_list_categories_public(self):
        """N'importe qui peut lister les catégories (sans authentification)."""
        response = self.client.get('/api/courses/categories/')
        self.assertEqual(response.status_code, 200)

    def test_create_category_admin(self):
        """Un administrateur peut créer une catégorie."""
        client = get_auth_client(self.admin)
        response = client.post(
            '/api/courses/categories/',
            {'name': 'Design', 'description': 'Cours design'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Category.objects.filter(name='Design').exists())

    def test_create_category_unauthenticated(self):
        """Un visiteur non connecté ne peut pas créer une catégorie."""
        response = self.client.post(
            '/api/courses/categories/',
            {'name': 'Hacking', 'description': '...'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)

    def test_slug_auto_generated(self):
        """Le slug est généré automatiquement depuis le nom."""
        client = get_auth_client(self.admin)
        response = client.post(
            '/api/courses/categories/',
            {'name': 'Développement Web'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        category = Category.objects.get(name='Développement Web')
        self.assertEqual(category.slug, 'developpement-web')

    def test_detail_category_public(self):
        """N'importe qui peut voir le détail d'une catégorie."""
        response = self.client.get(f'/api/courses/categories/{self.category.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Informatique')


class CatalogueTest(APITestCase):
    """Tests du catalogue public des formations."""

    def setUp(self):
        # Création des utilisateurs de test
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Jean', last_name='Formateur',
            role=User.Role.FORMATEUR,
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Marie', last_name='Apprenant',
        )
        self.categorie = Category.objects.create(name='Python')

        # Formation publiée : visible dans le catalogue
        self.formation_publiee = Formation.objects.create(
            formateur=self.formateur,
            categorie=self.categorie,
            titre='Python pour débutants',
            description='Apprenez Python',
            prix=5000,
            niveau=Formation.Level.DEBUTANT,
            is_published=True,
        )

        # Formation non publiée : invisible dans le catalogue
        self.formation_brouillon = Formation.objects.create(
            formateur=self.formateur,
            titre='Cours en préparation',
            description='Bientôt disponible',
            is_published=False,
        )

    def test_catalogue_shows_only_published(self):
        """Le catalogue ne montre que les formations publiées."""
        response = self.client.get('/api/courses/')
        self.assertEqual(response.status_code, 200)
        # results : liste paginée des formations
        titres = [f['titre'] for f in response.data['results']]
        self.assertIn('Python pour débutants', titres)
        self.assertNotIn('Cours en préparation', titres)

    def test_catalogue_public_no_auth_required(self):
        """Le catalogue est accessible sans authentification."""
        response = self.client.get('/api/courses/')
        self.assertEqual(response.status_code, 200)

    def test_catalogue_filter_by_niveau(self):
        """Filtrer les formations par niveau."""
        response = self.client.get('/api/courses/?niveau=debutant')
        self.assertEqual(response.status_code, 200)
        for formation in response.data['results']:
            self.assertEqual(formation['niveau'], 'debutant')

    def test_catalogue_filter_prix_min(self):
        """Filtrer les formations avec un prix minimum."""
        # Création d'une formation bon marché
        Formation.objects.create(
            formateur=self.formateur,
            titre='Cours gratuit',
            description='...',
            prix=0,
            is_published=True,
        )
        response = self.client.get('/api/courses/?prix_min=1000')
        self.assertEqual(response.status_code, 200)
        for formation in response.data['results']:
            self.assertGreaterEqual(float(formation['prix']), 1000)

    def test_catalogue_search(self):
        """La recherche textuelle fonctionne sur le titre."""
        response = self.client.get('/api/courses/?search=Python')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data['count'], 0)

    def test_detail_formation_publiee_public(self):
        """Le détail d'une formation publiée est visible par tous."""
        response = self.client.get(f'/api/courses/{self.formation_publiee.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['titre'], 'Python pour débutants')

    def test_detail_formation_brouillon_formateur(self):
        """Le formateur peut voir sa formation non publiée."""
        client = get_auth_client(self.formateur)
        response = client.get(f'/api/courses/{self.formation_brouillon.id}/')
        self.assertEqual(response.status_code, 200)

    def test_detail_formation_brouillon_autre_user(self):
        """Un apprenant ne peut pas voir une formation non publiée."""
        client = get_auth_client(self.apprenant)
        response = client.get(f'/api/courses/{self.formation_brouillon.id}/')
        self.assertEqual(response.status_code, 403)


class FormationManageTest(APITestCase):
    """Tests de gestion des formations par le formateur."""

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
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Pass123!',
            first_name='Admin', last_name='Test',
            role=User.Role.ADMINISTRATEUR,
        )
        self.categorie = Category.objects.create(name='Dev')
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            titre='Ma Formation',
            description='Description',
            prix=3000,
            is_published=True,
        )

    def test_formateur_can_create_formation(self):
        """Un formateur peut créer une nouvelle formation."""
        client = get_auth_client(self.formateur)
        response = client.post(
            '/api/courses/manage/',
            {
                'titre': 'Nouvelle Formation',
                'description': 'Super cours',
                'prix': 5000,
                'niveau': 'debutant',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        # Vérifie que le formateur est bien assigné automatiquement
        formation = Formation.objects.get(titre='Nouvelle Formation')
        self.assertEqual(formation.formateur, self.formateur)

    def test_apprenant_cannot_create_formation(self):
        """Un apprenant ne peut pas créer de formation."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            '/api/courses/manage/',
            {'titre': 'Tentative', 'description': '...', 'prix': 0},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_formateur_sees_only_own_formations(self):
        """Un formateur ne voit que ses propres formations dans /manage/."""
        client = get_auth_client(self.formateur)
        response = client.get('/api/courses/manage/')
        self.assertEqual(response.status_code, 200)
        for formation in response.data['results']:
            # Chaque formation retournée doit appartenir à ce formateur
            self.assertEqual(formation['formateur_nom'], self.formateur.full_name)

    def test_formateur_can_update_own_formation(self):
        """Un formateur peut modifier sa propre formation."""
        client = get_auth_client(self.formateur)
        response = client.patch(
            f'/api/courses/manage/{self.formation.id}/',
            {'titre': 'Titre Modifié'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.formation.refresh_from_db()
        self.assertEqual(self.formation.titre, 'Titre Modifié')

    def test_autre_formateur_cannot_update_formation(self):
        """Un formateur ne peut pas modifier la formation d'un autre."""
        client = get_auth_client(self.autre_formateur)
        response = client.patch(
            f'/api/courses/manage/{self.formation.id}/',
            {'titre': 'Vol de formation'},
            format='json',
        )
        self.assertEqual(response.status_code, 404)  # 404 car la formation n'est pas dans son queryset

    def test_admin_can_see_all_formations(self):
        """Un administrateur voit toutes les formations dans /manage/."""
        Formation.objects.create(
            formateur=self.autre_formateur,
            titre='Formation Autre',
            description='...',
        )
        client = get_auth_client(self.admin)
        response = client.get('/api/courses/manage/')
        self.assertEqual(response.status_code, 200)
        # L'admin doit voir au moins 2 formations
        self.assertGreaterEqual(response.data['count'], 2)

    def test_formateur_can_delete_own_formation(self):
        """Un formateur peut supprimer sa propre formation."""
        client = get_auth_client(self.formateur)
        response = client.delete(f'/api/courses/manage/{self.formation.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Formation.objects.filter(id=self.formation.id).exists())


class ModuleTest(APITestCase):
    """Tests de gestion des modules d'une formation."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Jean', last_name='Formateur',
            role=User.Role.FORMATEUR,
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@test.com', password='Pass123!',
            first_name='Bob', last_name='Apprenant',
        )
        self.formation = Formation.objects.create(
            formateur=self.formateur,
            titre='Ma Formation',
            description='...',
            is_published=True,
        )
        self.module = Module.objects.create(
            formation=self.formation,
            titre='Module 1 : Introduction',
            order=1,
        )

    def test_formateur_can_add_module(self):
        """Un formateur peut ajouter un module à sa formation."""
        client = get_auth_client(self.formateur)
        response = client.post(
            f'/api/courses/{self.formation.id}/modules/',
            {'formation': self.formation.id, 'titre': 'Module 2', 'order': 2},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Module.objects.filter(titre='Module 2').exists())

    def test_apprenant_cannot_add_module(self):
        """Un apprenant ne peut pas ajouter de module."""
        client = get_auth_client(self.apprenant)
        response = client.post(
            f'/api/courses/{self.formation.id}/modules/',
            {'formation': self.formation.id, 'titre': 'Tentative', 'order': 2},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_list_modules_of_formation(self):
        """On peut lister les modules d'une formation."""
        client = get_auth_client(self.formateur)
        response = client.get(f'/api/courses/{self.formation.id}/modules/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_update_module(self):
        """Un formateur peut modifier le titre d'un module."""
        client = get_auth_client(self.formateur)
        response = client.patch(
            f'/api/courses/modules/{self.module.id}/',
            {'titre': 'Titre modifié', 'formation': self.formation.id, 'order': 1},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.module.refresh_from_db()
        self.assertEqual(self.module.titre, 'Titre modifié')


class LessonTest(APITestCase):
    """Tests de gestion des leçons d'un module."""

    def setUp(self):
        self.formateur = User.objects.create_user(
            email='formateur@test.com', password='Pass123!',
            first_name='Jean', last_name='Formateur',
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
            titre='Leçon 1 : Introduction',
            content_type=Lesson.ContentType.VIDEO,
            video_url='https://youtube.com/watch?v=test',
            order=1,
        )

    def test_formateur_can_add_video_lesson(self):
        """Un formateur peut ajouter une leçon de type vidéo."""
        client = get_auth_client(self.formateur)
        response = client.post(
            f'/api/courses/modules/{self.module.id}/lessons/',
            {
                'module': self.module.id,
                'titre': 'Leçon 2 : Variables',
                'content_type': 'video',
                'video_url': 'https://youtube.com/watch?v=abc',
                'order': 2,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)

    def test_video_lesson_requires_url(self):
        """Une leçon vidéo sans URL doit retourner une erreur de validation."""
        client = get_auth_client(self.formateur)
        response = client.post(
            f'/api/courses/modules/{self.module.id}/lessons/',
            {
                'module': self.module.id,
                'titre': 'Leçon sans URL',
                'content_type': 'video',
                # video_url manquant intentionnellement
                'order': 3,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_preview_lesson_accessible_without_auth(self):
        """Une leçon en prévisualisation est visible dans le détail de la formation."""
        # La leçon est en prévisualisation (is_preview=True par défaut dans notre setUp : False)
        self.lesson.is_preview = True
        self.lesson.save()

        # Un visiteur non connecté peut voir le détail de la formation publiée
        response = self.client.get(f'/api/courses/{self.formation.id}/')
        self.assertEqual(response.status_code, 200)
        # La leçon est bien incluse dans les modules
        modules = response.data['modules']
        self.assertGreater(len(modules), 0)

    def test_delete_lesson(self):
        """Un formateur peut supprimer sa leçon."""
        client = get_auth_client(self.formateur)
        response = client.delete(f'/api/courses/lessons/{self.lesson.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Lesson.objects.filter(id=self.lesson.id).exists())
