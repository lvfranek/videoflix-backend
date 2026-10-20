import re
from unittest.mock import patch

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from auth_app.tasks import send_password_reset_email
from auth_app.utils import encode_uid

from .helpers import (
    DEFAULT_PASSWORD,
    create_user,
    log_in,
    run_jobs_immediately,
)

RESET_SENT = {'detail': 'An email has been sent to reset your password.'}
INVALID_LINK = {
    'non_field_errors': ['This reset link is invalid or has expired.']
}
NEW_PASSWORD = 'BrandNew!2026'


class PasswordResetRequestTests(APITestCase):
    """Tests for POST /api/password_reset/."""

    url = reverse('password_reset')

    def setUp(self):
        self.user = create_user()

    def request_reset(self, email):
        with run_jobs_immediately():
            return self.client.post(self.url, {'email': email}, format='json')

    def test_sends_reset_email_to_active_user(self):
        response = self.request_reset('user@example.com')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, RESET_SENT)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(
            (email.subject, email.to),
            ('Reset your Password', ['user@example.com']),
        )
        self.assertIn('Reset password', email.alternatives[0].content)

    def test_reset_email_contains_valid_frontend_link(self):
        self.request_reset('user@example.com')
        link = re.search(
            r'confirm_password\.html\?uid=(\S+)&token=(\S+)',
            mail.outbox[0].body,
        )
        self.assertEqual(link.group(1), encode_uid(self.user))
        self.assertTrue(
            default_token_generator.check_token(self.user, link.group(2))
        )

    def test_email_lookup_is_case_insensitive(self):
        self.request_reset('User@Example.com')
        self.assertEqual(mail.outbox[0].to, ['user@example.com'])

    def test_unknown_and_inactive_accounts_get_same_response_but_no_email(
        self,
    ):
        create_user(email='inactive@example.com', is_active=False)
        for email in ('nobody@example.com', 'inactive@example.com'):
            with self.subTest(email=email):
                response = self.request_reset(email)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data, RESET_SENT)
        self.assertEqual(len(mail.outbox), 0)

    def test_view_only_queues_job_without_database_lookup(self):
        with (
            patch('auth_app.tasks.django_rq.enqueue') as enqueue,
            self.assertNumQueries(0),
        ):
            self.client.post(
                self.url, {'email': 'user@example.com'}, format='json'
            )
        enqueue.assert_called_once_with(
            send_password_reset_email, 'user@example.com'
        )

    def test_invalid_email_is_rejected(self):
        response = self.request_reset('not-an-email')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)


class PasswordResetConfirmTests(APITestCase):
    """Tests for POST /api/password_confirm/<uidb64>/<token>/."""

    def setUp(self):
        self.user = create_user()
        self.uid = encode_uid(self.user)
        self.token = default_token_generator.make_token(self.user)

    def confirm(
        self,
        new_password=NEW_PASSWORD,
        confirm_password=NEW_PASSWORD,
        uid=None,
        token=None,
    ):
        url = reverse(
            'password_confirm', args=[uid or self.uid, token or self.token]
        )
        payload = {
            'new_password': new_password,
            'confirm_password': confirm_password,
        }
        return self.client.post(url, payload, format='json')

    def test_valid_link_sets_new_password(self):
        response = self.confirm()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {'detail': 'Your Password has been successfully reset.'},
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_login_works_with_new_password_only(self):
        self.confirm()
        self.assertEqual(
            log_in(self.client, password=DEFAULT_PASSWORD).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            log_in(self.client, password=NEW_PASSWORD).status_code,
            status.HTTP_200_OK,
        )

    def test_link_can_only_be_used_once(self):
        self.confirm()
        response = self.confirm(
            new_password='Another!2026', confirm_password='Another!2026'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, INVALID_LINK)

    def test_invalid_links_are_rejected(self):
        invalid_links = {
            'wrong token': {'token': 'abc-123'},
            'garbage uid': {'uid': '!!!'},
            'unknown user': {'uid': encode_uid(type(self.user)(pk=999))},
        }
        for case, link in invalid_links.items():
            with self.subTest(case=case):
                response = self.confirm(**link)
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST
                )
                self.assertEqual(response.data, INVALID_LINK)

    def test_invalid_passwords_are_rejected_with_specific_message(self):
        invalid_passwords = {
            'Passwords do not match.': (NEW_PASSWORD, 'Different!2026'),
            'This password is too common.': ('password123', 'password123'),
        }
        for message, (
            new_password,
            confirm_password,
        ) in invalid_passwords.items():
            with self.subTest(message=message):
                response = self.confirm(new_password, confirm_password)
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST
                )
                self.assertIn(message, response.data['non_field_errors'])

    def test_reset_ends_all_existing_sessions(self):
        """
        The reset token is created after the login, because a login
        invalidates earlier reset tokens by design.
        """
        log_in(self.client)
        self.user.refresh_from_db()
        self.token = default_token_generator.make_token(self.user)
        self.confirm()
        response = self.client.post(reverse('token_refresh'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
