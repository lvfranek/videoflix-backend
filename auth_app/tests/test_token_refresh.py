from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .helpers import create_user, log_in

INVALID_REFRESH = {'detail': 'Invalid refresh token.'}


class TokenRefreshTests(APITestCase):
    """Tests for POST /api/token/refresh/."""

    url = reverse('token_refresh')

    def setUp(self):
        self.user = create_user()
        log_in(self.client)

    def refresh_with(self, raw_token):
        self.client.cookies['refresh_token'] = raw_token
        return self.client.post(self.url)

    def test_valid_refresh_cookie_returns_new_access_token(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Token refreshed')
        new_access = AccessToken(response.data['access'])
        self.assertEqual(new_access['user_id'], str(self.user.id))

    def test_new_access_token_is_set_as_cookie(self):
        response = self.client.post(self.url)
        cookie = response.cookies['access_token']
        self.assertEqual(cookie.value, response.data['access'])
        self.assertTrue(cookie['httponly'])

    def test_missing_refresh_cookie_returns_400(self):
        del self.client.cookies['refresh_token']
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'detail': 'Refresh token missing.'})

    def test_invalid_refresh_tokens_return_401(self):
        blacklisted = RefreshToken.for_user(self.user)
        blacklisted.blacklist()
        invalid_tokens = {
            'garbage': 'not-a-jwt',
            'access token instead of refresh': str(AccessToken.for_user(self.user)),
            'blacklisted': str(blacklisted),
        }
        for case, raw_token in invalid_tokens.items():
            with self.subTest(case=case):
                response = self.refresh_with(raw_token)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
                self.assertEqual(response.data, INVALID_REFRESH)

    def test_refresh_fails_for_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_fails_for_deleted_user(self):
        self.user.delete()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
