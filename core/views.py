from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.generic import TemplateView

from companies.models import Company
from jobs.models import Job


def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recent_jobs"] = Job.objects.select_related("company").open()[:6]
        context["open_job_count"] = Job.objects.open().count()
        context["company_count"] = Company.objects.count()
        return context
