"""Background jobs of the auth app, executed by the django-rq worker."""

import django_rq
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction

from .utils import build_frontend_auth_link

User = get_user_model()


def send_activation_email(user_id, token):
    """Send the account activation link to a newly registered user."""
    user = User.objects.get(pk=user_id)
    activation_link = build_frontend_auth_link('activate.html', user, token)
    send_mail(
        subject='Confirm your email',
        message=f'Welcome to Videoflix!\n\nPlease activate your account:\n{activation_link}',
        from_email=None,
        recipient_list=[user.email],
    )


def queue_activation_email(user, token):
    """Queue the activation email once the user is committed to the database."""
    transaction.on_commit(lambda: django_rq.enqueue(send_activation_email, user.pk, token))
