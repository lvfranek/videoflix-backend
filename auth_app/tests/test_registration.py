from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from auth_app.utils import encode_uid

from .helpers import DEFAULT_PASSWORD, create_user, run_jobs_immediately

User = get_user_model()
GENERIC_ERROR = {'detail': 'Please check your input and try again.'}


class RegistrationTests(APITestCase):
    """Tests for POST /api/register/."""

    url = reverse('register')

    def register(self, email='new@example.com', password=DEFAULT_PASSWORD, confirmed_password=DEFAULT_PASSWORD):
        payload = {'email': email, 'password': password, 'confirmed_password': confirmed_password}
        with run_jobs_immediately(), self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, payload, format='json')

    def test_creates_inactive_user_and_returns_documented_body(self):
        response = self.register()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='new@example.com')
        self.assertFalse(user.is_active)
        self.assertEqual(user.username, 'new@example.com')
        self.assertEqual(response.data['user'], {'id': user.id, 'email': 'new@example.com'})
        self.assertTrue(response.data['token'])

    def test_stores_email_in_lowercase(self):
        self.register(email='Mixed.Case@Example.com')
        self.assertTrue(User.objects.filter(email='mixed.case@example.com').exists())

    def test_sends_activation_email_with_frontend_link(self):
        response = self.register()
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        user = User.objects.get(email='new@example.com')
        self.assertEqual(email.subject, 'Confirm your email')
        self.assertEqual(email.to, ['new@example.com'])
        expected_link = f'/pages/auth/activate.html?uid={encode_uid(user)}&token={response.data["token"]}'
        self.assertIn(expected_link, email.body)
        self.assertIn('Activate account', email.alternatives[0].content)

    def test_rejects_existing_email_case_insensitive_with_generic_error(self):
        create_user(email='taken@example.com')
        response = self.register(email='Taken@Example.com')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, GENERIC_ERROR)

    def test_rejects_invalid_input_with_generic_error(self):
        invalid_inputs = {
            'mismatching passwords': {'confirmed_password': 'Different!2026'},
            'too common password': {'password': 'password123', 'confirmed_password': 'password123'},
            'invalid email': {'email': 'not-an-email'},
        }
        for case, overrides in invalid_inputs.items():
            with self.subTest(case=case):
                response = self.register(**overrides)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data, GENERIC_ERROR)

    def test_rejects_missing_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, GENERIC_ERROR)

    def test_failed_registration_sends_no_email(self):
        self.register(confirmed_password='Different!2026')
        self.assertFalse(User.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_stale_auth_cookie_does_not_block_registration(self):
        self.client.cookies['access_token'] = 'expired-or-invalid'
        response = self.register()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
