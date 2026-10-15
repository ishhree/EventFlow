from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Event(models.Model):

    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        REGISTRATION_OPEN = "registration_open", "Registration Open"
        REGISTRATION_CLOSED = "registration_closed", "Registration Closed"
        ONGOING = "ongoing", "Ongoing"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    UPCOMING_STATUSES = [
        Status.UPCOMING,
        Status.REGISTRATION_OPEN,
        Status.REGISTRATION_CLOSED,
        Status.ONGOING,
    ]

    BADGE_CLASSES = {
        Status.UPCOMING: "bg-primary",
        Status.REGISTRATION_OPEN: "bg-success",
        Status.REGISTRATION_CLOSED: "bg-warning text-dark",
        Status.ONGOING: "bg-info text-dark",
        Status.COMPLETED: "bg-secondary",
        Status.CANCELLED: "bg-danger",
    }

    CHART_COLORS = {
        Status.UPCOMING: "#4f46e5",
        Status.REGISTRATION_OPEN: "#16a34a",
        Status.REGISTRATION_CLOSED: "#f59e0b",
        Status.ONGOING: "#0ea5e9",
        Status.COMPLETED: "#6b7280",
        Status.CANCELLED: "#dc2626",
    }

    name = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True
    )

    date = models.DateField()

    start_time = models.TimeField()

    end_time = models.TimeField()

    venue = models.CharField(
        max_length=200
    )

    capacity = models.PositiveIntegerField(
        validators=[
            MinValueValidator(
                1,
                message="Capacity must be greater than 0.",
            )
        ]
    )

    registration_deadline = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPCOMING,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events_created",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.name} ({self.date:%d %b %Y})"

    def clean(self):
        errors = {}

        if self.name is not None and not self.name.strip():
            errors["name"] = "Event name is required."

        if (
            self.start_time
            and self.end_time
            and self.end_time < self.start_time
        ):
            errors["end_time"] = (
                "End time cannot be earlier than start time."
            )

        if self.registration_deadline and self.date:
            deadline = self.registration_deadline

            if timezone.is_aware(deadline):
                deadline = timezone.localtime(deadline)

            if deadline.date() > self.date:
                errors["registration_deadline"] = (
                    "Registration deadline cannot be after the event date."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def badge_class(self):
        return self.BADGE_CLASSES.get(
            self.status,
            "bg-secondary",
        )

    @property
    def creator_name(self):
        if self.created_by_id:
            return (
                self.created_by.get_full_name()
                or self.created_by.username
            )

        return "Unknown"

    @property
    def registered_count(self):
        return self.registrations.filter(
            status=Registration.Status.REGISTERED
        ).count()

    @property
    def available_seats(self):
        return max(
            self.capacity - self.registered_count,
            0,
        )

    @property
    def is_full(self):
        return self.registered_count >= self.capacity

    @property
    def registration_open(self):
        if self.status != self.Status.REGISTRATION_OPEN:
            return False

        if self.is_full:
            return False

        if self.registration_deadline:
            deadline = self.registration_deadline

            if timezone.is_naive(deadline):
                deadline = timezone.make_aware(
                    deadline,
                    timezone.get_current_timezone(),
                )

            if timezone.now() > deadline:
                return False

        return True


class Profile(models.Model):

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        EVENT_MANAGER = "event_manager", "Event Manager"
        PARTICIPANT = "participant", "Participant"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PARTICIPANT,
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class Task(models.Model):

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        BLOCKED = "blocked", "Blocked"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="tasks",
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks_assigned",
    )

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )

    progress = models.PositiveIntegerField(
        default=0,
        validators=[
            MinValueValidator(
                0,
                message="Progress cannot be less than 0.",
            )
        ],
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["due_date", "-created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        errors = {}

        if self.title is not None and not self.title.strip():
            errors["title"] = "Task title is required."

        if self.progress > 100:
            errors["progress"] = (
                "Progress cannot be greater than 100."
            )

        if errors:
            raise ValidationError(errors)

    def update_progress_from_checklist(self):
        total_items = self.checklist_items.count()

        if total_items == 0:
            return

        completed_items = self.checklist_items.filter(
            completed=True
        ).count()

        self.progress = round(
            (completed_items / total_items) * 100
        )

        if self.progress == 100:
            self.status = self.Status.COMPLETED

        elif self.progress > 0:
            self.status = self.Status.IN_PROGRESS

        else:
            self.status = self.Status.TODO

        self.save(
            update_fields=[
                "progress",
                "status",
                "updated_at",
            ]
        )

    @property
    def assignee_name(self):
        if self.assigned_to_id:
            return (
                self.assigned_to.get_full_name()
                or self.assigned_to.username
            )

        return "Unassigned"

    @property
    def priority_badge_class(self):
        return {
            self.Priority.LOW: "bg-secondary",
            self.Priority.MEDIUM: "bg-primary",
            self.Priority.HIGH: "bg-warning text-dark",
            self.Priority.URGENT: "bg-danger",
        }.get(
            self.priority,
            "bg-secondary",
        )

    @property
    def status_badge_class(self):
        return {
            self.Status.TODO: "bg-secondary",
            self.Status.IN_PROGRESS: "bg-primary",
            self.Status.COMPLETED: "bg-success",
            self.Status.BLOCKED: "bg-danger",
        }.get(
            self.status,
            "bg-secondary",
        )


class ChecklistItem(models.Model):

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="checklist_items",
    )

    title = models.CharField(
        max_length=200,
    )

    completed = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["completed", "created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.title is not None and not self.title.strip():
            raise ValidationError(
                {
                    "title": "Checklist item title is required."
                }
            )


class Registration(models.Model):

    class Status(models.TextChoices):
        REGISTERED = "registered", "Registered"
        CANCELLED = "cancelled", "Cancelled"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="registrations",
    )

    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_registrations",
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.REGISTERED,
    )

    registered_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-registered_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["event", "participant"],
                name="unique_event_participant",
            )
        ]

    def __str__(self):
        return (
            f"{self.participant.username} - "
            f"{self.event.name}"
        )

    def clean(self):
        if self.participant_id:
            try:
                profile = self.participant.profile

                if profile.role != Profile.Role.PARTICIPANT:
                    raise ValidationError(
                        "Only participants can register for events."
                    )

            except Profile.DoesNotExist:
                raise ValidationError(
                    "The participant does not have a profile."
                )

        if self.event_id and self.status == self.Status.REGISTERED:

            if self.event.status != Event.Status.REGISTRATION_OPEN:
                raise ValidationError(
                    "Registration is not open for this event."
                )

            if self.event.is_full:
                raise ValidationError(
                    "This event is already full."
                )

            if (
                self.event.registration_deadline
                and timezone.now()
                > self.event.registration_deadline
            ):
                raise ValidationError(
                    "The registration deadline has passed."
                )
                
class Notification(models.Model):

    class NotificationType(models.TextChoices):
        REGISTRATION = "registration", "Registration"
        EVENT_UPDATE = "event_update", "Event Update"
        TASK_ASSIGNED = "task_assigned", "Task Assigned"
        GENERAL = "general", "General"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    title = models.CharField(max_length=150)

    message = models.TextField()

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL,
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.recipient}"