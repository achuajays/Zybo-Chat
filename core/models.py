from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Custom User model with online status tracking."""
    email = models.EmailField(unique=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username


class Message(models.Model):
    """Chat message between two users."""
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender} -> {self.receiver}: {self.content[:30]}"


# Signals to handle online status
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    user.is_online = True
    user.save(update_fields=['is_online'])

@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    user.is_online = False
    user.last_seen = timezone.now()
    user.save(update_fields=['is_online', 'last_seen'])
