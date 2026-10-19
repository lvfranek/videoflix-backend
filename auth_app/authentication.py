from rest_framework_simplejwt.authentication import JWTAuthentication

from .utils import ACCESS_TOKEN_COOKIE


class CookieJWTAuthentication(JWTAuthentication):
    """
    Authenticate requests with the JWT access token from an HttpOnly cookie.

    The frontend never sees the token itself, so it cannot send an
    Authorization header; the browser attaches the cookie instead.
    """

    def authenticate(self, request):
        raw_token = request.COOKIES.get(ACCESS_TOKEN_COOKIE)
        if raw_token is None:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
