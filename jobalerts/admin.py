from django.contrib import admin

from .models import ExternalJob, JobAlert, JobAlertMatch


@admin.register(JobAlert)
class JobAlertAdmin(admin.ModelAdmin):
    list_display = ("role_title", "user", "location", "frequency", "is_active")
    list_filter = ("is_active", "frequency", "email_enabled")
    search_fields = ("role_title", "skills", "user__email")


@admin.register(ExternalJob)
class ExternalJobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "source_name", "provider", "last_seen_at")
    list_filter = ("provider", "is_active")
    search_fields = ("title", "company", "location", "provider_id")


@admin.register(JobAlertMatch)
class JobAlertMatchAdmin(admin.ModelAdmin):
    list_display = ("alert", "job", "score", "email_sent_at", "created_at")
    list_filter = ("alert__frequency",)
