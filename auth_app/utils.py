from email.message import MIMEPart
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.core.exceptions import ObjectDoesNotExist
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings

ACCESS_TOKEN_COOKIE = 'access_token'
REFRESH_TOKEN_COOKIE = 'refresh_token'

EMAIL_TEMPLATE_DIR = 'auth_app/emails'
EMAIL_LOGO_CID = 'videoflix-logo'
EMAIL_LOGO_PATH = Path(__file__).resolve().parent / 'static' / 'auth_app' / 'images' / 'email_logo.png'


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


def get_user_from_uid(uidb64):
    """Return the user encoded in a URL-safe base64 uid, or None if it is invalid."""
    User = get_user_model()
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


def activate_user(uidb64, token):
    """Activate the account behind uid and token; return whether it succeeded."""
    user = get_user_from_uid(uidb64)
    if user is None or not account_activation_token.check_token(user, token):
        return False
    user.is_active = True
    user.save(update_fields=['is_active'])
    return True


def find_user_by_credentials(email, password):
    """Return the user matching email and password, or None."""
    User = get_user_model()
    user = User.objects.filter(email__iexact=email.strip()).first()
    if user is None:
        # Hash anyway so unknown emails take as long as wrong passwords (no user enumeration).
        User().set_password(password)
        return None
    return user if user.check_password(password) else None


def set_cookie(response, name, value, lifetime):
    """Set an HttpOnly auth cookie that the frontend JavaScript cannot read."""
    response.set_cookie(
        name,
        value,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
    )


def set_access_cookie(response, access_token):
    """Attach an access token as HttpOnly cookie."""
    set_cookie(response, ACCESS_TOKEN_COOKIE, str(access_token), jwt_settings.ACCESS_TOKEN_LIFETIME)


def set_auth_cookies(response, refresh_token):
    """Attach the access and refresh token of a login as HttpOnly cookies."""
    set_access_cookie(response, refresh_token.access_token)
    set_cookie(response, REFRESH_TOKEN_COOKIE, str(refresh_token), jwt_settings.REFRESH_TOKEN_LIFETIME)


def refresh_access_token(raw_refresh_token):
    """Return a new access token for a valid refresh token, or None if it is invalid or blacklisted."""
    serializer = TokenRefreshSerializer(data={'refresh': raw_refresh_token})
    try:
        serializer.is_valid(raise_exception=True)
    except (TokenError, AuthenticationFailed, ObjectDoesNotExist):
        return None
    return serializer.validated_data['access']


def build_frontend_auth_link(page, user, token):
    """Build a link to a frontend auth page that carries uid and token as query parameters."""
    query = urlencode({'uid': encode_uid(user), 'token': token})
    return f'{settings.FRONTEND_URL}/pages/auth/{page}?{query}'


def build_logo_attachment():
    """Return the Videoflix logo as inline image, referenced in templates via its content id."""
    logo = MIMEPart()
    logo.set_content(
        EMAIL_LOGO_PATH.read_bytes(),
        maintype='image',
        subtype='png',
        disposition='inline',
        cid=f'<{EMAIL_LOGO_CID}>',
    )
    return logo


def send_templated_email(subject, template_name, context, recipient):
    """Render the text and HTML version of an email template and send both with the inline logo."""
    context = {**context, 'logo_cid': EMAIL_LOGO_CID}
    text_body = render_to_string(f'{EMAIL_TEMPLATE_DIR}/{template_name}.txt', context)
    html_body = render_to_string(f'{EMAIL_TEMPLATE_DIR}/{template_name}.html', context)
    email = EmailMultiAlternatives(subject=subject, body=text_body, to=[recipient])
    email.attach_alternative(html_body, 'text/html')
    email.attach(build_logo_attachment())
    email.send()
