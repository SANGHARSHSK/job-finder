from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from .models import EmployerProfile, JobSeekerProfile, User


class RegistrationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=User.Role.choices,
        widget=forms.RadioSelect,
        label="I am a",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        # Always saves: the profile needs a saved user to point to.
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.save()
        if user.is_employer:
            EmployerProfile.objects.create(user=user)
        else:
            JobSeekerProfile.objects.create(user=user)
        return user