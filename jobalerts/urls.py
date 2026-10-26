from django.urls import path

from . import views

app_name = "jobalerts"

urlpatterns = [
    path("external-jobs/", views.ExternalJobListView.as_view(), name="external_jobs"),
    path("job-alerts/", views.JobAlertListView.as_view(), name="list"),
    path("job-alerts/new/", views.JobAlertCreateView.as_view(), name="create"),
    path("job-alerts/<int:pk>/edit/", views.JobAlertUpdateView.as_view(), name="update"),
    path("job-alerts/<int:pk>/delete/", views.JobAlertDeleteView.as_view(), name="delete"),
]
