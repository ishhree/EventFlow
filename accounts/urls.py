
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy


from django.urls import path
from . import views

from . import views
from .forms import (
    EmailLoginForm,
    EventFlowPasswordResetForm,
    EventFlowSetPasswordForm,
)

urlpatterns = [
    # ---------------------------------------------------------
    # PUBLIC PAGES
    # ---------------------------------------------------------

    path("", views.landing, name="landing"),
    path("register/", views.register, name="register"),

    # ---------------------------------------------------------
    # AUTHENTICATION
    # ---------------------------------------------------------

    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=EmailLoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),

    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/auth_form.html",
            form_class=EventFlowPasswordResetForm,
            success_url=reverse_lazy("password_reset_done"),
            extra_context={
                "title": "Forgot password",
                "subtitle": (
                    "Enter your email and we'll send a reset link."
                ),
                "button": "Send reset link",
            },
        ),
        name="password_reset",
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/auth_message.html",
            extra_context={
                "title": "Check your email",
                "message": (
                    "If an account exists for that email, "
                    "a reset link has been sent. "
                    "(In development, check the terminal "
                    "running the server.)"
                ),
            },
        ),
        name="password_reset_done",
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/auth_form.html",
            form_class=EventFlowSetPasswordForm,
            success_url=reverse_lazy("password_reset_complete"),
            extra_context={
                "title": "Set a new password",
                "subtitle": "Choose a strong password.",
                "button": "Change password",
            },
        ),
        name="password_reset_confirm",
    ),

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/auth_message.html",
            extra_context={
                "title": "Password changed",
                "message": (
                    "Your password has been updated. "
                    "You can now log in."
                ),
                "show_login": True,
            },
        ),
        name="password_reset_complete",
    ),

    # ---------------------------------------------------------
    # DASHBOARD AND PROFILE
    # ---------------------------------------------------------

    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("notifications/", views.notifications, name="notifications"),
    
    path(
        "my-registrations/",
        views.my_registrations,
        name="my_registrations",
    ),

    path(
        "notifications/",
        views.notifications,
        name="notifications",
    ),
    path("analytics/", views.analytics, name="analytics"),

    # ---------------------------------------------------------
    # EVENTS
    # ---------------------------------------------------------

    path("events/", views.event_list, name="event_list"),

    path(
        "calendar/",
        views.event_calendar,
        name="event_calendar",
    ),

    path("events/create/", views.event_create, name="event_create"),

    path(
        "events/<int:pk>/",
        views.event_detail,
        name="event_detail",
    ),

    path(
        "events/<int:pk>/edit/",
        views.event_edit,
        name="event_edit",
    ),

    path(
        "events/<int:pk>/delete/",
        views.event_delete,
        name="event_delete",
    ),

    path(
        "events/<int:pk>/register/",
        views.event_register,
        name="event_register",
    ),

    path(
        "events/<int:pk>/cancel-registration/",
        views.event_cancel_registration,
        name="event_cancel_registration",
    ),

    path(
        "events/<int:pk>/participants/",
        views.event_participants,
        name="event_participants",
    ),

    # ---------------------------------------------------------
    # TASKS
    # ---------------------------------------------------------

    path("tasks/", views.task_list, name="task_list"),
    path("tasks/my/", views.my_tasks, name="my_tasks"),
    path("tasks/create/", views.task_create, name="task_create"),

    path(
        "tasks/<int:pk>/",
        views.task_detail,
        name="task_detail",
    ),

    path(
        "tasks/<int:pk>/edit/",
        views.task_edit,
        name="task_edit",
    ),

    path(
        "tasks/<int:pk>/delete/",
        views.task_delete,
        name="task_delete",
    ),

    path(
        "tasks/<int:pk>/update-progress/",
        views.task_update_progress,
        name="task_update_progress",
    ),

    # ---------------------------------------------------------
    # CHECKLIST
    # ---------------------------------------------------------

    path(
        "tasks/<int:pk>/checklist/add/",
        views.checklist_add,
        name="checklist_add",
    ),

    path(
        "checklist/<int:pk>/toggle/",
        views.checklist_toggle,
        name="checklist_toggle",
    ),

    path(
        "checklist/<int:pk>/delete/",
        views.checklist_delete,
        name="checklist_delete",
    ),

path(
    "reports/events/download/",
    views.download_events_report,
    name="download_events_report",
),
path(
    "reports/registrations/download/",
    views.download_registrations_report,
    name="download_registrations_report",
),
path(
    "reports/tasks/download/",
    views.download_tasks_report,
    name="download_tasks_report",
),

path(
    "reports/events/download/",
    views.download_events_report,
    name="download_events_report",
),
path(
    "reports/registrations/download/",
    views.download_registrations_report,
    name="download_registrations_report",
),
path(
    "reports/tasks/download/",
    views.download_tasks_report,
    name="download_tasks_report",
),
path(
    "notifications/<int:pk>/read/",
    views.notification_mark_read,
    name="notification_mark_read",
),
path(
    "notifications/mark-all-read/",
    views.notifications_mark_all_read,
    name="notifications_mark_all_read",
),
]