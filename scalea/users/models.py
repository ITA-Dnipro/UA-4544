from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    is_startup = models.BooleanField(default=False)
    is_investor = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email or self.username
