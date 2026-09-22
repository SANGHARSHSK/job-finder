from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "location", "company_size")
    list_filter = ("company_size", "industry")
    search_fields = ("name", "location", "industry")