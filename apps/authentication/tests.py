from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User


class RegisterViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/register/'

    def test_register_success(self):
        data = {
            'email': 'new@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'Jean',
            'last_name': 'Dupont',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        self.assertEqual(response.data['user']['email'], 'new@example.com')
        self.assertTrue(User.objects.filter(email='new@example.com').exists())

    def test_register_as_formateur(self):
        data = {
            'email': 'formateur@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'Marie',
            'last_name': 'Formateur',
            'role': 'formateur',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email='formateur@example.com')
        self.assertEqual(user.role, User.Role.FORMATEUR)

    def test_register_admin_role_forbidden(self):
        data = {
            'email': 'hack@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'Hacker',
            'last_name': 'Man',
            'role': 'administrateur',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email='hack@example.com').exists())

    def test_register_password_mismatch(self):
        data = {
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'DifferentPass!',
            'first_name': 'A',
            'last_name': 'B',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register_duplicate_email(self):
        User.objects.create_user(
            email='exists@example.com', password='pass123',
            first_name='A', last_name='B',
        )
        data = {
            'email': 'exists@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'C',
            'last_name': 'D',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register_weak_password(self):
        data = {
            'email': 'weak@example.com',
            'password': '123',
            'password_confirm': '123',
            'first_name': 'A',
            'last_name': 'B',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, 400)


class LoginViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/login/'
        self.user = User.objects.create_user(
            email='login@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='Login',
        )

    def test_login_success(self):
        response = self.client.post(
            self.url, {'email': 'login@example.com', 'password': 'TestPass123!'}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('tokens', response.data)
        self.assertEqual(response.data['user']['email'], 'login@example.com')

    def test_login_wrong_password(self):
        response = self.client.post(
            self.url, {'email': 'login@example.com', 'password': 'wrong'}, format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_login_nonexistent_email(self):
        response = self.client.post(
            self.url, {'email': 'nope@example.com', 'password': 'TestPass123!'}, format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.url, {'email': 'login@example.com', 'password': 'TestPass123!'}, format='json'
        )
        self.assertEqual(response.status_code, 400)


class LogoutViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/logout/'
        self.user = User.objects.create_user(
            email='logout@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='Logout',
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')

    def test_logout_success(self):
        response = self.client.post(
            self.url, {'refresh': str(self.refresh)}, format='json'
        )
        self.assertEqual(response.status_code, 205)

    def test_logout_invalid_token(self):
        response = self.client.post(
            self.url, {'refresh': 'invalid-token'}, format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_logout_missing_token(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_logout_unauthenticated(self):
        client = APIClient()
        response = client.post(self.url, {'refresh': str(self.refresh)}, format='json')
        self.assertEqual(response.status_code, 401)


class TokenRefreshViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/token/refresh/'
        self.user = User.objects.create_user(
            email='refresh@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='Refresh',
        )
        self.refresh = RefreshToken.for_user(self.user)

    def test_refresh_success(self):
        response = self.client.post(
            self.url, {'refresh': str(self.refresh)}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)

    def test_refresh_invalid_token(self):
        response = self.client.post(
            self.url, {'refresh': 'invalid'}, format='json'
        )
        self.assertEqual(response.status_code, 401)


class ChangePasswordViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/password/change/'
        self.user = User.objects.create_user(
            email='change@example.com',
            password='OldPass123!',
            first_name='Test',
            last_name='Change',
        )
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

    def test_change_password_success(self):
        response = self.client.post(
            self.url,
            {'old_password': 'OldPass123!', 'new_password': 'NewPass456!'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass456!'))

    def test_change_password_wrong_old(self):
        response = self.client.post(
            self.url,
            {'old_password': 'WrongOld!', 'new_password': 'NewPass456!'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_change_password_unauthenticated(self):
        client = APIClient()
        response = client.post(
            self.url,
            {'old_password': 'OldPass123!', 'new_password': 'NewPass456!'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)


class PasswordResetViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='reset@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='Reset',
        )

    def test_request_reset_existing_email(self):
        response = self.client.post(
            '/api/auth/password/reset/',
            {'email': 'reset@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('uid', response.data)
        self.assertIn('token', response.data)

    def test_request_reset_nonexistent_email(self):
        response = self.client.post(
            '/api/auth/password/reset/',
            {'email': 'nobody@example.com'},
            format='json',
        )
        # Ne révèle pas l'existence de l'email
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('uid', response.data)

    def test_confirm_reset_success(self):
        # Obtenir uid + token
        response = self.client.post(
            '/api/auth/password/reset/',
            {'email': 'reset@example.com'},
            format='json',
        )
        uid = response.data['uid']
        token = response.data['token']

        # Confirmer le reset
        response = self.client.post(
            '/api/auth/password/reset/confirm/',
            {'uid': uid, 'token': token, 'new_password': 'BrandNew789!'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNew789!'))

    def test_confirm_reset_invalid_token(self):
        response = self.client.post(
            '/api/auth/password/reset/confirm/',
            {'uid': 'baduid', 'token': 'badtoken', 'new_password': 'NewPass123!'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
