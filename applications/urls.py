from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    path("jobs/<int:pk>/apply/", views.apply_to_job, name="apply"),
    path("applications/<int:pk>/resume/", views.resume_download, name="resume_download"),
]