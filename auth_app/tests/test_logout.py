from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .helpers import create_user, log_in

LOGOUT_SUCCESS = {
    'detail': (
        'Logout successful! All tokens will be deleted. '
        'Refresh token is now invalid.'
    )
}


class LogoutTests(APITestCase):
    """Tests for POST /api/logout/."""

    url = reverse('logout')

    def setUp(self):
        create_user()
        log_in(self.client)
        self.refresh_token = self.client.cookies['refresh_token'].value

    def assert_auth_cookies_deleted(self, response):
        for cookie_name in ('access_token', 'refresh_token'):
            with self.subTest(cookie=cookie_name):
                self.assertEqual(response.cookies[cookie_name].value, '')
                self.assertEqual(response.cookies[cookie_name]['max-age'], 0)

    def test_success_returns_documented_body_and_deletes_cookies(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, LOGOUT_SUCCESS)
        self.assert_auth_cookies_deleted(response)

    def test_refresh_token_is_blacklisted_after_logout(self):
        self.client.post(self.url)
        self.client.cookies['refresh_token'] = self.refresh_token
        response = self.client.post(reverse('token_refresh'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_refresh_cookie_returns_400_and_still_deletes_cookies(
        self,
    ):
        del self.client.cookies['refresh_token']
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'detail': 'Refresh token missing.'})
        self.assert_auth_cookies_deleted(response)

    def test_invalid_or_reused_refresh_token_still_logs_out(self):
        self.client.post(self.url)
        for raw_token in (self.refresh_token, 'not-a-jwt'):
            with self.subTest(token=raw_token[:10]):
                self.client.cookies['refresh_token'] = raw_token
                response = self.client.post(self.url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
