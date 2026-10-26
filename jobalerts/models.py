from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class JobAlert(TimeStampedModel):
    class Frequency(models.TextChoices):
        IMMEDIATE = "immediate", "As jobs are found"
        DAILY = "daily", "Daily digest"

    class EmploymentType(models.TextChoices):
        ANY = "", "Any type"
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_alerts"
    )
    role_title = models.CharField(max_length=150)
    role_description = models.TextField(blank=True)
    skills = models.TextField(help_text="Separate skills with commas.")
    location = models.CharField(max_length=120, blank=True)
    remote_only = models.BooleanField(default=False)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, blank=True, default=""
    )
    min_salary = models.PositiveIntegerField(null=True, blank=True)
    email_enabled = models.BooleanField(default=False)
    frequency = models.CharField(
        max_length=12, choices=Frequency.choices, default=Frequency.DAILY
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.role_title} alert for {self.user}"


class ExternalJob(TimeStampedModel):
    provider = models.CharField(max_length=40, default="jooble", db_index=True)
    provider_id = models.CharField(max_length=180)
    source_name = models.CharField(max_length=160, blank=True)
    title = models.CharField(max_length=250, db_index=True)
    company = models.CharField(max_length=250, blank=True)
    location = models.CharField(max_length=250, blank=True, db_index=True)
    snippet = models.TextField(blank=True)
    salary = models.CharField(max_length=160, blank=True)
    employment_type = models.CharField(max_length=100, blank=True)
    source_url = models.URLField(max_length=1000)
    source_updated_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_seen_at = models.DateTimeField(auto_now=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-source_updated_at", "-last_seen_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_id"], name="unique_external_job_provider_id"
            )
        ]

    def __str__(self):
        return f"{self.title} at {self.company or 'an employer'} ({self.provider})"


class JobAlertMatch(TimeStampedModel):
    alert = models.ForeignKey(JobAlert, on_delete=models.CASCADE, related_name="matches")
    job = models.ForeignKey(ExternalJob, on_delete=models.CASCADE, related_name="matches")
    score = models.PositiveSmallIntegerField(default=0)
    match_reasons = models.JSONField(default=list, blank=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["alert", "job"], name="unique_match_per_alert_job"
            )
        ]

    def __str__(self):
        return f"{self.job} matched {self.alert}"
