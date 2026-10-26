from django.views.generic import TemplateView

from companies.models import Company
from jobs.models import Job


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recent_jobs"] = Job.objects.select_related("company").open()[:6]
        context["open_job_count"] = Job.objects.open().count()
        context["company_count"] = Company.objects.count()
        return context