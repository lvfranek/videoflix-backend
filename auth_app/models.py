from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model with a unique email address.

    Users authenticate with their email; on registration the username
    is set to the email so the default Django tooling keeps working.
    """

    email = models.EmailField(unique=True)

    def __str__(self):
        return self.email
