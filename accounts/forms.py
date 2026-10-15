
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.core.exceptions import ValidationError

from .models import ChecklistItem, Event, Task


class EventForm(forms.ModelForm):

    class Meta:
        model = Event
        fields = [
            "name",
            "description",
            "date",
            "start_time",
            "end_time",
            "venue",
            "capacity",
            "registration_deadline",
            "status",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter event name",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Describe the event",
            }),
            "date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "start_time": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time",
            }),
            "end_time": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time",
            }),
            "venue": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter venue",
            }),
            "capacity": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
            }),
            "registration_deadline": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }),
            "status": forms.Select(attrs={
                "class": "form-select",
            }),
        }


class TaskForm(forms.ModelForm):

    class Meta:
        model = Task
        fields = [
            "event",
            "title",
            "description",
            "assigned_to",
            "due_date",
            "priority",
            "status",
            "progress",
        ]

        widgets = {
            "event": forms.Select(attrs={
                "class": "form-select",
            }),
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter task title",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Describe the task",
            }),
            "assigned_to": forms.Select(attrs={
                "class": "form-select",
            }),
            "due_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "priority": forms.Select(attrs={
                "class": "form-select",
            }),
            "status": forms.Select(attrs={
                "class": "form-select",
            }),
            "progress": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 0,
                "max": 100,
                "step": 1,
            }),
        }

    def clean_progress(self):
        progress = self.cleaned_data.get("progress")

        if progress is not None and not 0 <= progress <= 100:
            raise ValidationError(
                "Progress must be between 0 and 100."
            )

        return progress


class TaskProgressForm(forms.ModelForm):

    class Meta:
        model = Task
        fields = [
            "status",
            "progress",
        ]

        labels = {
            "status": "Task Status",
            "progress": "Progress (%)",
        }

        widgets = {
            "status": forms.Select(),
            "progress": forms.NumberInput(attrs={
                "min": 0,
                "max": 100,
                "step": 1,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            css = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )

            field.widget.attrs.setdefault("class", css)

    def clean_progress(self):
        progress = self.cleaned_data.get("progress")

        if progress is not None and not 0 <= progress <= 100:
            raise ValidationError(
                "Progress must be between 0 and 100."
            )

        return progress


class ChecklistItemForm(forms.ModelForm):

    class Meta:
        model = ChecklistItem
        fields = ["title"]

        labels = {
            "title": "Checklist Item",
        }

        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter checklist item",
            }),
        }

    def clean_title(self):
        title = self.cleaned_data.get("title")

        if title and not title.strip():
            raise ValidationError(
                "Checklist item title is required."
            )

        return title.strip() if title else title


class EmailLoginForm(AuthenticationForm):

    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Email address",
            "autocomplete": "username",
        }),
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Password",
            "autocomplete": "current-password",
        }),
    )


class EventFlowPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Email address",
            "autocomplete": "email",
        }),
    )


class EventFlowSetPasswordForm(forms.Form):

    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "New password",
        }),
    )

    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm new password",
        }),
    )

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")
        password_validation.validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError(
                "The two passwords do not match."
            )

        return cleaned_data