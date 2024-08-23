from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, RegexValidator


class UserProfile(models.Model):
    username = models.CharField(
        max_length=150,
        validators=[
            RegexValidator(
                regex=r"^[\w.@+-]+$",
                message="Username can only contain letters, digits and @/./+/-/_.",
            ),
        ],
        null=True,
        blank=True,
        unique=True
    )
    wallet_address = models.CharField(max_length=512, db_index=True, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
