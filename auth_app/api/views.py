from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.tasks import queue_activation_email
from auth_app.utils import account_activation_token, activate_user

from .serializers import RegistrationSerializer

GENERIC_INPUT_ERROR = 'Please check your input and try again.'


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
