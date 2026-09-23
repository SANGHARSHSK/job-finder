from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "job", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("applicant__user__username", "job__title")