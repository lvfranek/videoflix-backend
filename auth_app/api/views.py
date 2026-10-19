from django.contrib.auth.models import update_last_login
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.tasks import queue_activation_email
from auth_app.utils import (
    REFRESH_TOKEN_COOKIE,
    account_activation_token,
    activate_user,
    blacklist_refresh_token,
    delete_auth_cookies,
    refresh_access_token,
    set_access_cookie,
    set_auth_cookies,
)

from .serializers import LoginSerializer, RegistrationSerializer

GENERIC_INPUT_ERROR = 'Please check your input and try again.'
LOGOUT_MESSAGE = 'Logout successful! All tokens will be deleted. Refresh token is now invalid.'


class RegistrationView(APIView):
    """Register a new, inactive user and send the activation email in the background."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'detail': GENERIC_INPUT_ERROR}, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        token = account_activation_token.make_token(user)
        queue_activation_email(user, token)
        return Response({'user': serializer.data, 'token': token}, status=status.HTTP_201_CREATED)


class ActivationView(APIView):
    """Activate a user account via the uid and token from the activation email."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        if not activate_user(uidb64, token):
            return Response({'message': 'Activation failed.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Account successfully activated.'}, status=status.HTTP_200_OK)


class LoginView(APIView):
    """Log a user in and set the JWT access and refresh token as HttpOnly cookies."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        update_last_login(None, user)
        response = Response({
            'detail': 'Login successful',
            'user': {'id': user.id, 'username': user.username},
        }, status=status.HTTP_200_OK)
        set_auth_cookies(response, RefreshToken.for_user(user))
        return response


class CookieTokenRefreshView(APIView):
    """Issue a new access token cookie based on the refresh token cookie."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE)
        if refresh_token is None:
            return Response({'detail': 'Refresh token missing.'}, status=status.HTTP_400_BAD_REQUEST)
        access_token = refresh_access_token(refresh_token)
        if access_token is None:
            return Response({'detail': 'Invalid refresh token.'}, status=status.HTTP_401_UNAUTHORIZED)
        response = Response({'detail': 'Token refreshed', 'access': access_token}, status=status.HTTP_200_OK)
        set_access_cookie(response, access_token)
        return response


class LogoutView(APIView):
    """Log the user out by blacklisting the refresh token and deleting both auth cookies."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE)
        if refresh_token is None:
            response = Response({'detail': 'Refresh token missing.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            blacklist_refresh_token(refresh_token)
            response = Response({'detail': LOGOUT_MESSAGE}, status=status.HTTP_200_OK)
        delete_auth_cookies(response)
        return response
