from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from .models import EmployerProfile, JobSeekerProfile, User


class UniqueEmailMixin:
    """Lowercases the email and rejects duplicates, ignoring case."""

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        duplicates = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class RegistrationForm(UniqueEmailMixin, UserCreationForm):
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

    @transaction.atomic
    def save(self, commit=True):
        # Always saves: the profile needs a saved user to point to.
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.save()
        user.get_profile()  # creates the profile matching the role
        return user


class UserUpdateForm(UniqueEmailMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True


class JobSeekerProfileForm(forms.ModelForm):
    class Meta:
        model = JobSeekerProfile
        fields = ("phone", "location", "headline", "bio", "skills")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "skills": forms.Textarea(attrs={"rows": 3}),
        }


class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ("job_title", "phone")