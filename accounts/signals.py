from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """Every new user automatically gets a Profile.
    Superusers (created via createsuperuser) become Admins."""
    if created:
        role = Profile.Role.ADMIN if instance.is_superuser else Profile.Role.PARTICIPANT
        Profile.objects.get_or_create(user=instance, defaults={"role": role})