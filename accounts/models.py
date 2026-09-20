from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.conf import settings

from core.models import TimeStampedModel


# Create your models here.

phone_validator = RegexValidator(
    regex=r"^\+?[0-9 ()-]{7,20}$",
    message="Enter a valid phone number.",
)

class User(AbstractUser):
    class Role(models.TextChoices):
        JOB_SEEKER = "job_seeker", "job seeker"
        EMPLOYER = "employer", "Employer"

    email = models.EmailField("email address", unique = True)
    role = models.CharField(
        max_length = 20,
        choices = Role.choices,
        blank = True,
        default = "",
    )  

    @property
    def is_job_seeker(self):
        return self.role == self.Role.JOB_SEEKER

    @property
    def is_employer(self):
        return self.role == self.Role.EMPLOYER

class JobSeekerProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE,
        related_name = "job_seeker_profile",
    )
    phone = models.CharField(max_length=20, blank=True, validators=[phone_validator])
    location = models.CharField(max_length=100, blank=True)
    headline = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
    skills = models.TextField(blank=True, help_text="Comma-separated list of skills.")

    def __str__(self):
        return f"Job seeker profile: {self.user.username}"

class EmployerProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE,
        related_name = "employer_profile",
    )    

    job_title = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True, validators=[phone_validator])

    def __str__(self):
        return f"Employer profile: {self.user.username}"