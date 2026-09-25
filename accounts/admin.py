from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import EmployerProfile, JobSeekerProfile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_active", "date_joined")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    fieldsets = UserAdmin.fieldsets + (("Role", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Role", {"fields": ("email", "role")}),)


@admin.register(JobSeekerProfile)
class JobSeekerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "location", "headline", "created_at")
    list_filter = ("location",)
    search_fields = ("user__username", "user__email", "location", "headline", "skills")

    def has_add_permission(self, request):
        # Profiles are only ever created via registration or get_profile().
        return False


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "job_title", "created_at")
    search_fields = ("user__username", "user__email", "job_title")

    def has_add_permission(self, request):
        return False