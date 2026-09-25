from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "location", "industry", "company_size", "created_at")
    list_filter = ("company_size", "industry")
    search_fields = ("name", "owner__user__username", "location", "industry")