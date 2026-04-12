from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, UserProfile


class UserManagerTest(TestCase):
    def test_create_user_with_email(self):
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='testpass123')

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_email_is_unique(self):
        User.objects.create_user(
            email='unique@example.com',
            password='pass123',
            first_name='A',
            last_name='B',
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='unique@example.com',
                password='pass456',
                first_name='C',
                last_name='D',
            )

    def test_email_is_normalized(self):
        user = User.objects.create_user(
            email='test@EXAMPLE.COM',
            password='pass123',
            first_name='A',
            last_name='B',
        )
        self.assertEqual(user.email, 'test@example.com')


class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Jean',
            last_name='Dupont',
        )

    def test_str_returns_email(self):
        self.assertEqual(str(self.user), 'test@example.com')

    def test_full_name(self):
        self.assertEqual(self.user.full_name, 'Jean Dupont')

    def test_default_role_is_apprenant(self):
        self.assertEqual(self.user.role, User.Role.APPRENANT)
        self.assertTrue(self.user.is_apprenant)

    def test_is_formateur_property(self):
        self.user.role = User.Role.FORMATEUR
        self.user.save()
        self.assertTrue(self.user.is_formateur)
        self.assertFalse(self.user.is_apprenant)

    def test_is_administrateur_property(self):
        self.user.role = User.Role.ADMINISTRATEUR
        self.user.save()
        self.assertTrue(self.user.is_administrateur)

    def test_is_administrateur_includes_also_admin(self):
        self.user.role = User.Role.FORMATEUR
        self.user.is_also_admin = True
        self.user.save()
        self.assertTrue(self.user.is_formateur)
        self.assertTrue(self.user.is_administrateur)


class UserProfileSignalTest(TestCase):
    def test_profile_auto_created(self):
        user = User.objects.create_user(
            email='signal@example.com',
            password='pass123',
            first_name='A',
            last_name='B',
        )
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)

    def test_profile_str(self):
        user = User.objects.create_user(
            email='profil@example.com',
            password='pass123',
            first_name='A',
            last_name='B',
        )
        self.assertEqual(str(user.profile), 'Profil de profil@example.com')


class MeEndpointTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='me@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Me',
        )
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

    def test_me_get_authenticated(self):
        response = self.client.get('/api/users/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], 'me@example.com')
        self.assertEqual(response.data['first_name'], 'Test')
        self.assertIn('profile', response.data)

    def test_me_get_unauthenticated(self):
        client = APIClient()
        response = client.get('/api/users/me/')
        self.assertEqual(response.status_code, 401)

    def test_me_patch_update_name(self):
        response = self.client.patch(
            '/api/users/me/',
            {'first_name': 'Nouveau'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Nouveau')

    def test_me_patch_update_profile(self):
        response = self.client.patch(
            '/api/users/me/',
            {'profile': {'phone': '+237600000000', 'bio': 'Ma bio'}},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, '+237600000000')
        self.assertEqual(self.user.profile.bio, 'Ma bio')


class UserListEndpointTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
            role=User.Role.ADMINISTRATEUR,
        )
        self.apprenant = User.objects.create_user(
            email='apprenant@example.com',
            password='pass123',
            first_name='Apprenant',
            last_name='User',
        )

    def test_admin_can_list_users(self):
        token = RefreshToken.for_user(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

    def test_apprenant_cannot_list_users(self):
        token = RefreshToken.for_user(self.apprenant)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_view_user_detail(self):
        token = RefreshToken.for_user(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        response = self.client.get(f'/api/users/{self.apprenant.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], 'apprenant@example.com')
