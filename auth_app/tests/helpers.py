"""Shared helpers for the auth app tests."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse

DEFAULT_PASSWORD = 'Videoflix!2026'


def create_user(
    email='user@example.com', password=DEFAULT_PASSWORD, is_active=True
):
    """
    Create a user the same way the registration does (username equals
    email).
    """
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password=password,
        is_active=is_active,
    )


def run_jobs_immediately():
    """
    Patch the RQ queue so background jobs run synchronously inside the
    test.
    """
    return patch(
        'auth_app.tasks.django_rq.enqueue',
        side_effect=lambda job, *args: job(*args),
    )


def log_in(client, email='user@example.com', password=DEFAULT_PASSWORD):
    """
    Log in through the API; the test client keeps the auth cookies for
    later requests.
    """
    payload = {'email': email, 'password': password}
    return client.post(reverse('login'), payload, format='json')
