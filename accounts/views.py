
import calendar
from datetime import date

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .decorators import role_required
from .forms import (
    ChecklistItemForm,
    EventForm,
    TaskForm,
    TaskProgressForm,
)
from .models import (
    ChecklistItem,
    Event,
    Notification,
    Profile,
    Registration,
    Task,
)
import csv
from django.http import HttpResponse

SORT_OPTIONS = {
    "newest": ("Newest", ["-created_at", "-id"]),
    "oldest": ("Oldest", ["created_at", "id"]),
    "date_asc": ("Date: Soonest", ["date", "start_time"]),
    "date_desc": ("Date: Latest", ["-date", "-start_time"]),
}


def landing(request):
    return render(request, "landing.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()

            Profile.objects.get_or_create(
                user=user,
                defaults={
                    "role": Profile.Role.PARTICIPANT
                },
            )

            login(request, user)

            messages.success(
                request,
                "Account created successfully. Welcome to EventFlow!",
            )

            return redirect("dashboard")

    else:
        form = UserCreationForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


@login_required
def dashboard(request):
    events = Event.objects.select_related("created_by")

    upcoming_events = events.filter(
        status__in=Event.UPCOMING_STATUSES
    ).order_by(
        "date",
        "start_time",
    )

    tasks = Task.objects.select_related(
        "event",
        "assigned_to",
    )

    context = {
        "events": events,
        "upcoming_events": upcoming_events[:5],
        "total_events": events.count(),
        "upcoming_count": upcoming_events.count(),
        "completed_count": events.filter(
            status=Event.Status.COMPLETED
        ).count(),
        "cancelled_count": events.filter(
            status=Event.Status.CANCELLED
        ).count(),
        "total_tasks": tasks.count(),
        "completed_tasks": tasks.filter(
            status=Task.Status.COMPLETED
        ).count(),
        "pending_tasks": tasks.exclude(
            status=Task.Status.COMPLETED
        ).count(),
    }

    return render(
        request,
        "accounts/dashboard_placeholder.html",
        context,
    )


@login_required
def my_registrations(request):
    """Show all event registrations belonging to the logged-in user."""
    registrations = (
        Registration.objects
        .filter(participant=request.user)
        .select_related("event")
        .order_by("-event__date")
    )

    return render(
        request,
        "events/my_registrations.html",
        {"registrations": registrations},
    )

@login_required
def profile(request):
    user = request.user

    profile_obj, created = Profile.objects.get_or_create(
        user=user,
        defaults={
            "role": Profile.Role.PARTICIPANT
        },
    )

    if request.method == "POST":
        user.first_name = request.POST.get(
            "first_name",
            "",
        ).strip()

        user.last_name = request.POST.get(
            "last_name",
            "",
        ).strip()

        user.email = request.POST.get(
            "email",
            "",
        ).strip()

        profile_obj.phone = request.POST.get(
            "phone",
            "",
        ).strip()

        user.save()
        profile_obj.save()

        messages.success(
            request,
            "Profile updated successfully.",
        )

        return redirect("profile")

    return render(
        request,
        "accounts/profile.html",
        {"profile": profile_obj},
    )


@login_required
def event_list(request):
    q = request.GET.get(
        "q",
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    ).strip()

    sort = request.GET.get(
        "sort",
        "newest",
    )

    if sort not in SORT_OPTIONS:
        sort = "newest"

    if status not in Event.Status.values:
        status = ""

    events = Event.objects.select_related(
        "created_by",
    )

    if q:
        events = events.filter(
            Q(name__icontains=q)
            | Q(venue__icontains=q)
            | Q(description__icontains=q)
        )

    if status:
        events = events.filter(
            status=status,
        )

    events = events.order_by(
        *SORT_OPTIONS[sort][1],
    )

    return render(
        request,
        "events/event_list.html",
        {
            "events": events,
            "q": q,
            "status": status,
            "sort": sort,
            "status_choices": Event.Status.choices,
            "sort_choices": [
                (key, value[0])
                for key, value in SORT_OPTIONS.items()
            ],
            "has_filters": bool(q or status),
        },
    )


# =========================================================
# EVENT CALENDAR
# =========================================================

@login_required
def event_calendar(request):
    """
    Display a monthly calendar containing existing database events.
    """

    today = date.today()

    # Read the requested year and month.
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))

        if not 1 <= month <= 12:
            raise ValueError

        if not 1 <= year <= 9999:
            raise ValueError

    except (TypeError, ValueError):
        year = today.year
        month = today.month

    # Build a calendar with Monday as the first weekday.
    calendar_builder = calendar.Calendar(
        firstweekday=calendar.MONDAY,
    )

    calendar_weeks = calendar_builder.monthdatescalendar(
        year,
        month,
    )

    # Include the adjacent-month days visible in the grid.
    first_day = calendar_weeks[0][0]
    last_day = calendar_weeks[-1][-1]

    events = Event.objects.filter(
        date__gte=first_day,
        date__lte=last_day,
    ).select_related(
        "created_by",
    ).order_by(
        "date",
        "start_time",
    )

    # Group events by date for the template.
    events_by_date = {}

    for event in events:
        events_by_date.setdefault(
            event.date,
            [],
        ).append(event)

    weeks = []

    for week in calendar_weeks:
        days = []

        for day in week:
            days.append({
                "date": day,
                "day_number": day.day,
                "in_month": day.month == month,
                "is_today": day == today,
                "events": events_by_date.get(day, []),
            })

        weeks.append(days)

    # Previous month navigation.
    if month == 1:
        previous_month = 12
        previous_year = year - 1
    else:
        previous_month = month - 1
        previous_year = year

    # Next month navigation.
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    context = {
        "weeks": weeks,
        "month_name": calendar.month_name[month],
        "current_year": year,
        "current_month": month,
        "previous_month": previous_month,
        "previous_year": previous_year,
        "next_month": next_month,
        "next_year": next_year,
        "today": today,
    }

    return render(
        request,
        "events/event_calendar.html",
        context,
    )


@login_required
def event_detail(request, pk):
    event = get_object_or_404(
        Event.objects.select_related("created_by"),
        pk=pk,
    )

    user_registration = None

    if request.user.is_authenticated:
        user_registration = (
            Registration.objects.filter(
                event=event,
                participant=request.user,
            )
            .first()
        )

    return render(
        request,
        "events/event_detail.html",
        {
            "event": event,
            "user_registration": user_registration,
        },
    )


@role_required("admin", "event_manager")
def event_create(request):
    form = EventForm(
        request.POST or None,
    )

    if request.method == "POST" and form.is_valid():
        event = form.save(
            commit=False,
        )

        event.created_by = request.user
        event.save()

        messages.success(
            request,
            "Event created successfully.",
        )

        return redirect(
            "event_detail",
            pk=event.pk,
        )

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "mode": "create",
        },
    )


@role_required("admin", "event_manager")
def event_edit(request, pk):
    event = get_object_or_404(
        Event,
        pk=pk,
    )

    form = EventForm(
        request.POST or None,
        instance=event,
    )

    if request.method == "POST" and form.is_valid():
        form.save()

        messages.success(
            request,
            "Event updated successfully.",
        )

        return redirect(
            "event_detail",
            pk=event.pk,
        )

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "mode": "edit",
            "event": event,
        },
    )


@role_required("admin", "event_manager")
def event_delete(request, pk):
    event = get_object_or_404(
        Event,
        pk=pk,
    )

    if request.method == "POST":
        event.delete()

        messages.success(
            request,
            "Event deleted successfully.",
        )

        return redirect("event_list")

    return render(
        request,
        "events/event_confirm_delete.html",
        {"event": event},
    )


# =========================================================
# EVENT REGISTRATION
# =========================================================


@login_required
@require_POST
def event_register(request, pk):
    # Only participants can register.
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        messages.error(
            request,
            "Your account does not have a profile.",
        )
        return redirect("event_detail", pk=pk)

    if profile.role != Profile.Role.PARTICIPANT:
        messages.error(
            request,
            "Only participants can register for events.",
        )
        return redirect("event_detail", pk=pk)

    event = get_object_or_404(Event, pk=pk)

    existing_registration = Registration.objects.filter(
        event=event,
        participant=request.user,
    ).first()

    if (
        existing_registration
        and existing_registration.status
        == Registration.Status.REGISTERED
    ):
        messages.info(
            request,
            "You are already registered for this event.",
        )
        return redirect("event_detail", pk=event.pk)

    # Check registration rules.
    if not event.registration_open:
        if event.is_full:
            messages.error(
                request,
                "This event is already full.",
            )
        elif event.status != Event.Status.REGISTRATION_OPEN:
            messages.error(
                request,
                "Registration is not currently open for this event.",
            )
        else:
            messages.error(
                request,
                "Registration for this event is closed.",
            )

        return redirect("event_detail", pk=event.pk)

    try:
        with transaction.atomic():
            if existing_registration:
                existing_registration.status = (
                    Registration.Status.REGISTERED
                )
                existing_registration.save(
                    update_fields=["status", "updated_at"]
                )
            else:
                Registration.objects.create(
                    event=event,
                    participant=request.user,
                    status=Registration.Status.REGISTERED,
                )

    except IntegrityError:
        messages.error(
            request,
            "You could not be registered for this event.",
        )
        return redirect("event_detail", pk=event.pk)

    # Notify the event creator after successful registration.
    if event.created_by and event.created_by != request.user:
        Notification.objects.create(
            recipient=event.created_by,
            title="New Event Registration",
            message=(
                f"{request.user.get_full_name() or request.user.username} "
                f"registered for {event.name}."
            ),
            notification_type=(
                Notification.NotificationType.REGISTRATION
            ),
        )

    messages.success(
        request,
        f"You are successfully registered for {event.name}.",
    )

    return redirect("event_detail", pk=event.pk)

notification_type=Notification.NotificationType.REGISTRATION,



@login_required
@require_POST
def event_cancel_registration(request, pk):

    event = get_object_or_404(
        Event,
        pk=pk,
    )

    registration = get_object_or_404(
        Registration,
        event=event,
        participant=request.user,
        status=Registration.Status.REGISTERED,
    )

    registration.status = Registration.Status.CANCELLED

    registration.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    messages.success(
        request,
        f"Your registration for {event.name} has been cancelled.",
    )

    return redirect(
        "event_detail",
        pk=event.pk,
    )


# =========================================================
# EVENT PARTICIPANTS
# =========================================================

@role_required("admin", "event_manager")
def event_participants(request, pk):
    event = get_object_or_404(Event, pk=pk)

    registrations = (
        Registration.objects.filter(event=event)
        .select_related("participant")
        .order_by(
            "participant__first_name",
            "participant__last_name",
            "participant__email",
        )
    )

    active_registrations = registrations.filter(
        status=Registration.Status.REGISTERED
    )

    cancelled_registrations = registrations.filter(
        status=Registration.Status.CANCELLED
    )

    context = {
        "event": event,
        "registrations": registrations,
        "active_registrations": active_registrations,
        "total_registered": active_registrations.count(),
        "cancelled_count": cancelled_registrations.count(),
        "remaining_seats": event.available_seats,
    }

    return render(
        request,
        "events/participants.html",
        context,
    )


# =========================================================
# TASKS
# =========================================================

@login_required
def task_list(request):

    event_id = request.GET.get(
        "event",
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    ).strip()

    priority = request.GET.get(
        "priority",
        "",
    ).strip()

    q = request.GET.get(
        "q",
        "",
    ).strip()

    tasks = Task.objects.select_related(
        "event",
        "assigned_to",
    )

    if event_id:
        tasks = tasks.filter(
            event_id=event_id,
        )

    if status and status in Task.Status.values:
        tasks = tasks.filter(
            status=status,
        )

    if priority and priority in Task.Priority.values:
        tasks = tasks.filter(
            priority=priority,
        )

    if q:
        tasks = tasks.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(event__name__icontains=q)
        )

    events = Event.objects.order_by(
        "date",
        "start_time",
    )

    return render(
        request,
        "tasks/task_list.html",
        {
            "tasks": tasks,
            "events": events,
            "event_id": event_id,
            "status": status,
            "priority": priority,
            "q": q,
            "status_choices": Task.Status.choices,
            "priority_choices": Task.Priority.choices,
        },
    )


@login_required
def task_detail(request, pk):

    task = get_object_or_404(
        Task.objects.select_related(
            "event",
            "assigned_to",
        ).prefetch_related(
            "checklist_items",
        ),
        pk=pk,
    )

    checklist_items = task.checklist_items.all()

    checklist_form = ChecklistItemForm()

    return render(
        request,
        "tasks/task_detail.html",
        {
            "task": task,
            "checklist_form": checklist_form,
            "checklist_items": checklist_items,
            "checklist_has_items": checklist_items.exists(),
        },
    )


@role_required("admin", "event_manager")
def task_create(request):

    form = TaskForm(
        request.POST or None,
    )

    if request.method == "POST" and form.is_valid():

        task = form.save()
        if task.assigned_to and task.assigned_to != request.user:
           Notification.objects.create(
        recipient=task.assigned_to,
        title="New Task Assigned",
        message=(
            f"You have been assigned the task "
            f"'{task.title}' for the event "
            f"'{task.event.name}'."
        ), 
        notification_type=(
            Notification.NotificationType.TASK_ASSIGNED
        ),
    )

        messages.success(
            request,
            "Task created successfully.",
        )

        return redirect(
            "task_detail",
            pk=task.pk,
        )

    return render(
        request,
        "tasks/task_form.html",
        {
            "form": form,
            "mode": "create",
        },
    )



@role_required("admin", "event_manager")
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)

    form = TaskForm(
        request.POST or None,
        instance=task,
    )

    if request.method == "POST" and form.is_valid():
        form.save()

        messages.success(
            request,
            "Task updated successfully.",
        )

        return redirect("task_detail", pk=task.pk)

    return render(
        request,
        "tasks/task_form.html",
        {
            "form": form,
            "mode": "edit",
            "task": task,
        },
    )


@role_required("admin", "event_manager")
def task_delete(request, pk):

    task = get_object_or_404(
        Task,
        pk=pk,
    )

    if request.method == "POST":

        task.delete()

        messages.success(
            request,
            "Task deleted successfully.",
        )

        return redirect("task_list")

    return render(
        request,
        "tasks/task_confirm_delete.html",
        {"task": task},
    )


@login_required
def my_tasks(request):

    tasks = Task.objects.select_related(
        "event",
        "assigned_to",
    ).prefetch_related(
        "checklist_items",
    ).filter(
        assigned_to=request.user,
    )

    return render(
        request,
        "tasks/my_tasks.html",
        {"tasks": tasks},
    )


@login_required
def task_update_progress(request, pk):

    task = get_object_or_404(
        Task.objects.select_related(
            "event",
            "assigned_to",
        ),
        pk=pk,
    )

    if task.checklist_items.exists():

        messages.info(
            request,
            "This task uses its checklist to calculate progress automatically.",
        )

        return redirect(
            "task_detail",
            pk=task.pk,
        )

    if task.assigned_to_id != request.user.id:
        raise PermissionDenied

    form = TaskProgressForm(
        request.POST or None,
        instance=task,
    )

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Task progress updated successfully.",
        )

        return redirect(
            "task_detail",
            pk=task.pk,
        )

    return render(
        request,
        "tasks/task_update_progress.html",
        {
            "form": form,
            "task": task,
        },
    )


# =========================================================
# CHECKLIST
# =========================================================

@role_required("admin", "event_manager")
def checklist_add(request, pk):

    task = get_object_or_404(
        Task,
        pk=pk,
    )

    form = ChecklistItemForm(
        request.POST or None,
    )

    if request.method == "POST" and form.is_valid():

        checklist_item = form.save(
            commit=False,
        )

        checklist_item.task = task

        checklist_item.save()

        task.update_progress_from_checklist()

        messages.success(
            request,
            "Checklist item added successfully.",
        )

        return redirect(
            "task_detail",
            pk=task.pk,
        )

    if request.method == "POST":

        messages.error(
            request,
            "Please enter a valid checklist item.",
        )

    return redirect(
        "task_detail",
        pk=task.pk,
    )


@login_required
@require_POST
def checklist_toggle(request, pk):

    checklist_item = get_object_or_404(
        ChecklistItem.objects.select_related(
            "task",
            "task__assigned_to",
        ),
        pk=pk,
    )

    task = checklist_item.task

    if task.assigned_to_id != request.user.id:
        raise PermissionDenied

    checklist_item.completed = not checklist_item.completed

    checklist_item.save(
        update_fields=[
            "completed",
            "updated_at",
        ]
    )

    task.update_progress_from_checklist()

    return redirect(
        "task_detail",
        pk=task.pk,
    )


@role_required("admin", "event_manager")
@require_POST
def checklist_delete(request, pk):

    checklist_item = get_object_or_404(
        ChecklistItem.objects.select_related(
            "task",
        ),
        pk=pk,
    )

    task = checklist_item.task

    checklist_item.delete()

    if task.checklist_items.exists():
        task.update_progress_from_checklist()

    messages.success(
        request,
        "Checklist item deleted successfully.",
    )

    return redirect(
        "task_detail",
        pk=task.pk,
    )

    
@login_required
def notifications(request):
    """Display notifications belonging to the logged-in user."""
    user_notifications = Notification.objects.filter(
        recipient=request.user
    )

    unread_count = user_notifications.filter(
        is_read=False
    ).count()

    context = {
        "notifications": user_notifications,
        "unread_count": unread_count,
    }

    return render(
        request,
        "accounts/notifications.html",
        context,
    )


@login_required
@require_POST
def notification_mark_read(request, pk):
    """Mark one of the current user's notifications as read."""
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user,
    )

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    messages.success(request, "Notification marked as read.")

    return redirect("notifications")


@login_required
@require_POST
def notifications_mark_all_read(request):
    """Mark all unread notifications of the current user as read."""
    Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(is_read=True)

    messages.success(request, "All notifications marked as read.")

    return redirect("notifications")
    
@login_required
@role_required("admin", "event_manager")
def analytics(request):
    total_events = Event.objects.count()

    total_registrations = Registration.objects.filter(
        status=Registration.Status.REGISTERED
    ).count()

    total_tasks = Task.objects.count()

    completed_tasks = Task.objects.filter(
        status=Task.Status.COMPLETED
    ).count()

    pending_tasks = Task.objects.exclude(
        status=Task.Status.COMPLETED
    ).count()

    completion_percentage = (
        round((completed_tasks / total_tasks) * 100)
        if total_tasks
        else 0
    )

    context = {
        "total_events": total_events,
        "total_registrations": total_registrations,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "completion_percentage": completion_percentage,
        "upcoming_events": Event.objects.filter(
            status__in=Event.UPCOMING_STATUSES
        ).count(),
        "completed_events": Event.objects.filter(
            status=Event.Status.COMPLETED
        ).count(),
        "cancelled_events": Event.objects.filter(
            status=Event.Status.CANCELLED
        ).count(),
    }

    return render(
        request,
        "accounts/analytics.html",
        context,
    )
    
# =========================================================
# REPORTS - CSV DOWNLOADS
# =========================================================

@role_required("admin", "event_manager")
def download_events_report(request):
    response = HttpResponse(
        content_type="text/csv; charset=utf-8"
    )
    response["Content-Disposition"] = (
        'attachment; filename="eventflow_events.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        "Event Name",
        "Date",
        "Venue",
        "Status",
        "Total Registrations",
        "Completed Tasks",
        "Pending Tasks",
    ])

    events = Event.objects.all().order_by("date")

    for event in events:
        registrations = Registration.objects.filter(
            event=event,
            status=Registration.Status.REGISTERED,
        ).count()

        event_tasks = Task.objects.filter(event=event)

        completed = event_tasks.filter(
            status=Task.Status.COMPLETED
        ).count()

        pending = event_tasks.exclude(
            status=Task.Status.COMPLETED
        ).count()

        writer.writerow([
            event.name,
            event.date,
            event.venue,
            event.status,
            registrations,
            completed,
            pending,
        ])

    return response


@role_required("admin", "event_manager")
def download_registrations_report(request):
    response = HttpResponse(
        content_type="text/csv; charset=utf-8"
    )
    response["Content-Disposition"] = (
        'attachment; filename="eventflow_registrations.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        "Participant Name",
        "Email",
        "Event Name",
        "Registration Status",
        "Registered At",
    ])

    registrations = Registration.objects.select_related(
        "event",
        "participant",
    ).order_by("-registered_at")

    for registration in registrations:
        participant = registration.participant

        writer.writerow([
            participant.get_full_name() or participant.username,
            participant.email,
            registration.event.name,
            registration.status,
            registration.registered_at,
        ])

    return response


@role_required("admin", "event_manager")
def download_tasks_report(request):
    response = HttpResponse(
        content_type="text/csv; charset=utf-8"
    )
    response["Content-Disposition"] = (
        'attachment; filename="eventflow_tasks.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        "Task Name",
        "Event",
        "Priority",
        "Status",
        "Assigned To",
        "Due Date",
    ])

    tasks = Task.objects.select_related(
        "event",
        "assigned_to",
    ).order_by("due_date")

    for task in tasks:
        assignee = (
            task.assigned_to.get_full_name()
            or task.assigned_to.username
            if task.assigned_to
            else "Unassigned"
        )

        writer.writerow([
            task.title,
            task.event.name,
            task.priority,
            task.status,
            assignee,
            task.due_date,
        ])

    return response
