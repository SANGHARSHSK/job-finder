from django.contrib import admin

from .models import Job, SavedJob


@admin.action(description="Mark selected jobs as Removed (moderation)")
def mark_as_removed(modeladmin, request, queryset):
    queryset.update(status=Job.Status.REMOVED)


@admin.action(description="Mark selected jobs as Open")
def mark_as_open(modeladmin, request, queryset):
    queryset.update(status=Job.Status.OPEN)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title", "company", "location", "employment_type",
        "experience_level", "status", "created_at",
    )
    list_filter = ("status", "employment_type", "experience_level")
    search_fields = ("title", "company__name", "location", "description")
    date_hierarchy = "created_at"
    actions = [mark_as_removed, mark_as_open]


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("applicant", "job", "created_at")
    search_fields = ("applicant__user__username", "job__title")

    def has_add_permission(self, request):
        # Bookmarks are only ever created via the toggle-save view.
        return False