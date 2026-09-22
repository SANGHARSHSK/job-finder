from django.urls import path

from . import views

app_name = "companies"

urlpatterns = [
    path("company/", views.company_edit, name="edit"),
    path("companies/<int:pk>/", views.CompanyDetailView.as_view(), name="detail"),
]