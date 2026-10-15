from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Profile


DEMO_USERS = [
    (
        "admin@eventflow.com",
        "Admin",
        "User",
        "Admin@12345",
        Profile.Role.ADMIN,
        "9000000001",
    ),
    (
        "manager@eventflow.com",
        "Maya",
        "Manager",
        "Manager@12345",
        Profile.Role.EVENT_MANAGER,
        "9000000002",
    ),
    (
        "participant@eventflow.com",
        "Pete",
        "Participant",
        "Participant@12345",
        Profile.Role.PARTICIPANT,
        "9000000003",
    ),
]


class Command(BaseCommand):
    help = "Create demo users (admin, manager, participant) for development."

    def handle(self, *args, **options):

        for email, first, last, password, role, phone in DEMO_USERS:

            if User.objects.filter(username=email).exists():
                self.stdout.write(f"Exists: {email}")
                continue

            if role == Profile.Role.ADMIN:
                user = User.objects.create_superuser(
                    email,
                    email,
                    password,
                    first_name=first,
                    last_name=last,
                )
            else:
                user = User.objects.create_user(
                    email,
                    email,
                    password,
                    first_name=first,
                    last_name=last,
                )

            user.profile.role = role
            user.profile.phone = phone
            user.profile.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {role}: {email}"
                )
            )