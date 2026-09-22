from django.contrib import admin

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "location", "employment_type", "status", "created_at")
    list_filter = ("status", "employment_type", "experience_level")
    search_fields = ("title", "company__name", "location")