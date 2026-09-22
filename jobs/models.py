from django.db import models
from django.urls import reverse

from companies.models import Company
from core.models import TimeStampedModel


class Job(TimeStampedModel):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"

    class ExperienceLevel(models.TextChoices):
        ENTRY = "entry", "Entry level"
        MID = "mid", "Mid level"
        SENIOR = "senior", "Senior level"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        REMOVED = "removed", "Removed"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=150, db_index=True)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    location = models.CharField(max_length=100, db_index=True)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, db_index=True
    )
    experience_level = models.CharField(
        max_length=20, choices=ExperienceLevel.choices, db_index=True
    )
    salary_min = models.PositiveIntegerField(blank=True, null=True)
    salary_max = models.PositiveIntegerField(blank=True, null=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True
    )

    class Meta:
        indexes = [models.Index(fields=["status", "-created_at"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} @ {self.company.name}"

    def get_absolute_url(self):
        return reverse("jobs:detail", kwargs={"pk": self.pk})

    @property
    def is_open(self):
        return self.status == self.Status.OPEN