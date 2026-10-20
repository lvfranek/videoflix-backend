from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from auth_app.utils import (
    blacklist_all_refresh_tokens,
    find_user_by_credentials,
    get_user_from_reset_link,
)

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Validates sign-up data and creates an inactive user.

    The email allows 150 characters like the username field, because
    the email is stored as username as well.
    """

    email = serializers.EmailField(max_length=150)
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'confirmed_password')
        extra_kwargs = {'password': {'write_only': True}}

    def validate_email(self, value):
        """
        Normalize the email and reject addresses that are already
        registered.
        """
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
    """
    Checks email and password and provides the matching, active user.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = find_user_by_credentials(attrs['email'], attrs['password'])
        if user is None:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError(
                'Please activate your account first.'
            )
        attrs['user'] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Validates the email address a password reset link should be sent to.
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        """
        Normalize the email so the lookup in the background job matches.
        """
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Validates a password reset link (uid and token from the context) and
    the new password.
    """

    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = get_user_from_reset_link(
            self.context['uidb64'], self.context['token']
        )
        if user is None:
            raise serializers.ValidationError(
                'This reset link is invalid or has expired.'
            )
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError('Passwords do not match.')
        validate_password(attrs['new_password'], user=user)
        attrs['user'] = user
        return attrs

    def save(self):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        blacklist_all_refresh_tokens(user)
        return user
