import os
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse

from accounts.models import JobSeekerProfile
from core.models import TimeStampedModel
from jobs.models import Job

MAX_RESUME_SIZE_MB = 5
ALLOWED_RESUME_EXTENSIONS = ["pdf", "doc", "docx"]


def validate_resume_size(file):
    if file.size > MAX_RESUME_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Resume file must be under {MAX_RESUME_SIZE_MB} MB.")


def resume_upload_path(instance, filename):
    # A random name means a resume can't be found or guessed by URL alone;
    # access is controlled entirely by the resume_download view below.
    ext = os.path.splitext(filename)[1].lower()
    return f"resumes/{uuid.uuid4().hex}{ext}"


class Application(TimeStampedModel):
    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        UNDER_REVIEW = "under_review", "Under Review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED = "rejected", "Rejected"
        HIRED = "hired", "Hired"
        WITHDRAWN = "withdrawn", "Withdrawn"

    # PROTECT: a job with applications can't be hard-deleted (Step 3.4's
    # JobDeleteView already handles the resulting ProtectedError).
    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="applications")
    applicant = models.ForeignKey(
        JobSeekerProfile, on_delete=models.CASCADE, related_name="applications"
    )
    resume = models.FileField(
        upload_to=resume_upload_path,
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_RESUME_EXTENSIONS),
            validate_resume_size,
        ],
    )
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)

    # Which status changes an employer may make, keyed by current status.
    EMPLOYER_ALLOWED_TRANSITIONS = {
        Status.APPLIED: {Status.UNDER_REVIEW, Status.SHORTLISTED, Status.REJECTED, Status.HIRED},
        Status.UNDER_REVIEW: {Status.SHORTLISTED, Status.REJECTED, Status.HIRED},
        Status.SHORTLISTED: {Status.REJECTED, Status.HIRED},
        Status.REJECTED: set(),
        Status.HIRED: set(),
        Status.WITHDRAWN: set(),
    }

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job", "applicant"], name="unique_application_per_job_applicant"
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.applicant.user.username} -> {self.job.title}"

    def get_absolute_url(self):
        return reverse("applications:resume_download", kwargs={"pk": self.pk})

    def can_employer_transition_to(self, new_status):
        return new_status in self.EMPLOYER_ALLOWED_TRANSITIONS.get(self.status, set())

    def can_withdraw(self):
        return self.status in {self.Status.APPLIED, self.Status.UNDER_REVIEW}