from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    Token generator for account activation links.

    The activation state is part of the hash, so a token becomes
    invalid as soon as the account has been activated.
    """

    def _make_hash_value(self, user, timestamp):
        return f'{user.pk}{user.is_active}{timestamp}'


account_activation_token = AccountActivationTokenGenerator()


def encode_uid(user):
    """Return the user's primary key as URL-safe base64 string."""
    return urlsafe_base64_encode(force_bytes(user.pk))


def build_frontend_auth_link(page, user, token):
    """Build a link to a frontend auth page that carries uid and token as query parameters."""
    query = urlencode({'uid': encode_uid(user), 'token': token})
    return f'{settings.FRONTEND_URL}/pages/auth/{page}?{query}'
