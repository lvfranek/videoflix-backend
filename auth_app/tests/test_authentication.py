from datetime import timedelta

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from auth_app.authentication import CookieJWTAuthentication

from .helpers import create_user


class CookieJWTAuthenticationTests(APITestCase):
    """Tests for authenticating requests via the access_token cookie."""

    def setUp(self):
        self.user = create_user()
        self.authentication = CookieJWTAuthentication()

    def authenticate(self, cookie=None, **headers):
        request = APIRequestFactory().get('/', **headers)
        if cookie is not None:
            request.COOKIES['access_token'] = cookie
        return self.authentication.authenticate(request)

    def test_valid_cookie_authenticates_user(self):
        user, _ = self.authenticate(str(AccessToken.for_user(self.user)))
        self.assertEqual(user, self.user)

    def test_request_without_cookie_is_anonymous(self):
        self.assertIsNone(self.authenticate())

    def test_authorization_header_is_ignored(self):
        header = f'Bearer {AccessToken.for_user(self.user)}'
        self.assertIsNone(self.authenticate(HTTP_AUTHORIZATION=header))

    def test_invalid_tokens_are_rejected(self):
        expired = AccessToken.for_user(self.user)
        expired.set_exp(lifetime=-timedelta(minutes=1))
        for case, raw_token in {
            'garbage': 'not-a-jwt',
            'expired': str(expired),
        }.items():
            with (
                self.subTest(case=case),
                self.assertRaises(AuthenticationFailed),
            ):
                self.authenticate(raw_token)

    def test_inactive_user_is_rejected(self):
        token = str(AccessToken.for_user(self.user))
        self.user.is_active = False
        self.user.save()
        with self.assertRaises(AuthenticationFailed):
            self.authenticate(token)
