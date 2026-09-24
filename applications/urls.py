from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    path("jobs/<int:pk>/apply/", views.apply_to_job, name="apply"),
    path("applications/", views.MyApplicationsListView.as_view(), name="my_applications"),
    path("applications/<int:pk>/withdraw/", views.withdraw_application, name="withdraw"),
    path("applications/<int:pk>/resume/", views.resume_download, name="resume_download"),
    path(
        "employer/jobs/<int:pk>/applicants/",
        views.JobApplicantsListView.as_view(),
        name="job_applicants",
    ),
    path(
        "employer/applications/<int:pk>/status/",
        views.update_application_status,
        name="update_status",
    ),
]