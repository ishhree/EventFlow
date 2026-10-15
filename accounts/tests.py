from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Event

User = get_user_model()


class BaseEMSTestCase(TestCase):
    """Create common users and roles for EMS tests."""

    @classmethod
    def setUpTestData(cls):
        for role in ("admin", "event_manager", "participant"):
            Group.objects.get_or_create(name=role)

        cls.admin = User.objects.create_superuser(
            username="test_admin",
            email="test_admin@example.com",
            password="TestPass123!",
        )

        cls.manager = User.objects.create_user(
            username="test_manager",
            email="test_manager@example.com",
            password="TestPass123!",
        )
        cls.manager.groups.add(Group.objects.get(name="event_manager"))

        cls.participant = User.objects.create_user(
            username="test_participant",
            email="test_participant@example.com",
            password="TestPass123!",
        )
        cls.participant.groups.add(Group.objects.get(name="participant"))


class AuthenticationTests(BaseEMSTestCase):

    def test_admin_user_exists(self):
        self.assertTrue(User.objects.filter(username="test_admin").exists())

    def test_manager_user_exists(self):
        self.assertTrue(User.objects.filter(username="test_manager").exists())

    def test_participant_user_exists(self):
        self.assertTrue(
            User.objects.filter(username="test_participant").exists()
        )

    def test_valid_login(self):
        logged_in = self.client.login(
            username="test_admin",
            password="TestPass123!",
        )
        self.assertTrue(logged_in)

    def test_invalid_login(self):
        logged_in = self.client.login(
            username="test_admin",
            password="WrongPassword123!",
        )
        self.assertFalse(logged_in)

    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)


class DashboardTests(BaseEMSTestCase):

    def test_dashboard_redirects_or_denies_anonymous_user(self):
        response = self.client.get(reverse("dashboard"))
        self.assertIn(response.status_code, (302, 401, 403))

    def test_admin_can_access_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)


class RoleAuthorizationTests(BaseEMSTestCase):

    def test_admin_role_is_configured(self):
        self.assertTrue(self.admin.is_superuser)

    def test_manager_has_correct_group(self):
        self.assertTrue(
            self.manager.groups.filter(name="event_manager").exists()
        )

    def test_participant_has_correct_group(self):
        self.assertTrue(
            self.participant.groups.filter(name="participant").exists()
        )


class EventTests(BaseEMSTestCase):

    def setUp(self):
        self.event = Event.objects.create(
            name="EMS Test Event",
            date=timezone.localdate() + timedelta(days=7),
            start_time="10:00",
            end_time="12:00",
            capacity=100,
            created_by=self.admin,
)

    def test_event_is_created(self):
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_event_name_is_saved(self):
        self.assertEqual(self.event.name, "EMS Test Event")

    def test_event_creator_is_saved(self):
        self.assertEqual(self.event.created_by, self.admin)

    def test_event_list_requires_login_or_loads(self):
        response = self.client.get(reverse("event_list"))
        self.assertIn(response.status_code, (200, 302, 401, 403))

    def test_admin_can_open_event_list(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("event_list"))
        self.assertEqual(response.status_code, 200)
