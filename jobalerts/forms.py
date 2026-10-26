from django import forms

from .models import JobAlert


class JobAlertForm(forms.ModelForm):
    class Meta:
        model = JobAlert
        fields = (
            "role_title",
            "role_description",
            "skills",
            "location",
            "remote_only",
            "employment_type",
            "min_salary",
            "email_enabled",
            "frequency",
            "is_active",
        )
        widgets = {
            "role_description": forms.Textarea(attrs={"rows": 4}),
            "skills": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "role_title": "Target role",
            "role_description": "What kind of work are you looking for?",
            "skills": "Skills to match",
            "location": "Preferred location",
            "remote_only": "Only show remote roles",
            "employment_type": "Employment type",
            "min_salary": "Minimum salary in the source currency",
            "email_enabled": "Email me when matching jobs are found",
            "frequency": "Email frequency",
            "is_active": "Keep this alert active",
        }
