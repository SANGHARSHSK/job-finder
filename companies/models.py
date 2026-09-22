from django.db import models
from django.urls import reverse

from accounts.models import EmployerProfile
from core.models import TimeStampedModel


class Company(TimeStampedModel):
    class CompanySize(models.TextChoices):
        MICRO = "1-10", "1–10 employees"
        SMALL = "11-50", "11–50 employees"
        MEDIUM = "51-200", "51–200 employees"
        LARGE = "201-1000", "201–1,000 employees"
        ENTERPRISE = "1000+", "1,000+ employees"

    owner = models.OneToOneField(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name="company",
    )
    name = models.CharField(max_length=150, db_index=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    company_size = models.CharField(
        max_length=20, choices=CompanySize.choices, blank=True
    )

    class Meta:
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("companies:detail", kwargs={"pk": self.pk})