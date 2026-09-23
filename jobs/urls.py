from django.urls import path

from . import views

app_name = "jobs"

urlpatterns = [
    path("jobs/", views.JobListView.as_view(), name="list"),
    path("jobs/<int:pk>/", views.JobDetailView.as_view(), name="detail"),
    path("employer/jobs/", views.EmployerJobListView.as_view(), name="employer_job_list"),
    path(
        "employer/jobs/new/",
        views.require_company(views.JobCreateView.as_view()),
        name="create",
    ),
    path("employer/jobs/<int:pk>/edit/", views.JobUpdateView.as_view(), name="update"),
    path("employer/jobs/<int:pk>/delete/", views.JobDeleteView.as_view(), name="delete"),
]