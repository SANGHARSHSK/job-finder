from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.db.models import Q
from django.utils import timezone
from companies.models import Company
from core.models import TimeStampedModel
from accounts.models import JobSeekerProfile


class JobQuerySet(models.QuerySet):
    def open(self):
        cutoff = timezone.now() - timedelta(days=Job.CONFIRMATION_INTERVAL_DAYS)
        return self.filter(
            status=Job.Status.OPEN,
            last_confirmed_at__gte=cutoff,
        )

    def search(self, query):
        if not query:
            return self
        return self.filter(
            Q(title__icontains=query)
            | Q(company__name__icontains=query)
            | Q(location__icontains=query)
        )

class Job(TimeStampedModel):
    objects = JobQuerySet.as_manager()
    CONFIRMATION_INTERVAL_DAYS = 30

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
    last_confirmed_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        indexes = [models.Index(fields=["status", "-created_at"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} @ {self.company.name}"

    def get_absolute_url(self):
        return reverse("jobs:detail", kwargs={"pk": self.pk})

    @property
    def is_open(self):
        return self.status == self.Status.OPEN and not self.needs_confirmation

    @property
    def needs_confirmation(self):
        cutoff = timezone.now() - timedelta(days=self.CONFIRMATION_INTERVAL_DAYS)
        return self.last_confirmed_at is None or self.last_confirmed_at < cutoff

class SavedJob(TimeStampedModel):
    applicant = models.ForeignKey(
        JobSeekerProfile, on_delete=models.CASCADE, related_name="saved_jobs"
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="saved_by")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["applicant", "job"], name="unique_saved_job_per_applicant"
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.applicant.user.username} saved {self.job.title}"
