from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.utils import account_activation_token

from .serializers import RegistrationSerializer

GENERIC_INPUT_ERROR = 'Please check your input and try again.'


class RegistrationView(APIView):
    """Register a new, inactive user and return the activation token."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'detail': GENERIC_INPUT_ERROR}, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        response_data = {
            'user': serializer.data,
            'token': account_activation_token.make_token(user),
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
