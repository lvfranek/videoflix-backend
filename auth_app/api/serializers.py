from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from auth_app.utils import find_user_by_credentials

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    """Validates sign-up data and creates an inactive user."""

    # max_length matches the username field, which stores the email as well
    email = serializers.EmailField(max_length=150)
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'confirmed_password')
        extra_kwargs = {'password': {'write_only': True}}

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Email is already in use.')
        return email

    def validate(self, attrs):
        if attrs['password'] != attrs['confirmed_password']:
            raise serializers.ValidationError('Passwords do not match.')
        validate_password(attrs['password'])
        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        return User.objects.create_user(
            username=email,
            email=email,
            password=validated_data['password'],
            is_active=False,
        )


class LoginSerializer(serializers.Serializer):
    """Checks email and password and provides the matching, active user."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = find_user_by_credentials(attrs['email'], attrs['password'])
        if user is None:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('Please activate your account first.')
        attrs['user'] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Validates the email address a password reset link should be sent to."""

    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()
