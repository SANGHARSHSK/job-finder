from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "job", "status", "created_at", "updated_at")
    list_filter = ("status", "job__company")
    search_fields = ("applicant__user__username", "applicant__user__email", "job__title")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        # Applications are only ever created via the apply flow, which also
        # enforces resume validation and the one-application-per-job rule.
        return False