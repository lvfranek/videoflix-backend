from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from .helpers import create_user, log_in

INVALID_CREDENTIALS = {'non_field_errors': ['Invalid email or password.']}


class LoginTests(APITestCase):
    """Tests for POST /api/login/."""

    def setUp(self):
        self.user = create_user()

    def test_success_returns_documented_body(self):
        response = log_in(self.client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'detail': 'Login successful',
            'user': {'id': self.user.id, 'username': 'user@example.com'},
        })

    def test_success_sets_http_only_token_cookies(self):
        response = log_in(self.client)
        expected_lifetimes = {'access_token': 30 * 60, 'refresh_token': 24 * 60 * 60}
        for cookie_name, lifetime in expected_lifetimes.items():
            with self.subTest(cookie=cookie_name):
                cookie = response.cookies[cookie_name]
                self.assertTrue(cookie.value)
                self.assertTrue(cookie['httponly'])
                self.assertEqual(cookie['samesite'], 'Lax')
                self.assertEqual(cookie['max-age'], lifetime)

    def test_cookies_are_secure_unless_debug(self):
        self.assertTrue(log_in(self.client).cookies['access_token']['secure'])
        with override_settings(DEBUG=True):
            self.assertFalse(log_in(self.client).cookies['access_token']['secure'])

    def test_success_records_login_and_refresh_token(self):
        log_in(self.client)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)
        self.assertEqual(OutstandingToken.objects.filter(user=self.user).count(), 1)

    def test_email_is_case_insensitive(self):
        response = log_in(self.client, email='User@Example.com')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_wrong_password_and_unknown_email_get_identical_response(self):
        wrong_password = log_in(self.client, password='Wrong!2026')
        unknown_email = log_in(self.client, email='nobody@example.com')
        for response in (wrong_password, unknown_email):
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data, INVALID_CREDENTIALS)
            self.assertNotIn('access_token', response.cookies)

    def test_inactive_user_is_asked_to_activate_only_with_correct_password(self):
        create_user(email='inactive@example.com', is_active=False)
        correct = log_in(self.client, email='inactive@example.com')
        wrong = log_in(self.client, email='inactive@example.com', password='Wrong!2026')
        self.assertEqual(correct.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(correct.data, {'non_field_errors': ['Please activate your account first.']})
        self.assertEqual(wrong.data, INVALID_CREDENTIALS)

    def test_missing_fields_are_rejected(self):
        response = self.client.post(reverse('login'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('password', response.data)
