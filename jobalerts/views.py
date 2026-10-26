from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.mixins import JobSeekerRequiredMixin

from .forms import JobAlertForm
from .models import ExternalJob, JobAlert


class ExternalJobListView(LoginRequiredMixin, JobSeekerRequiredMixin, ListView):
    template_name = "jobalerts/external_jobs.html"
    context_object_name = "external_jobs"
    paginate_by = 20

    def get_queryset(self):
        queryset = ExternalJob.objects.filter(
            is_active=True,
            last_seen_at__gte=timezone.now() - timedelta(days=30),
            matches__alert__user=self.request.user,
            matches__alert__is_active=True,
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(company__icontains=query)
                | Q(location__icontains=query)
                | Q(snippet__icontains=query)
            )
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["provider_configured"] = bool(
            settings.JOOBLE_API_KEY and settings.JOOBLE_API_URL
        )
        return context


class JobAlertListView(JobSeekerRequiredMixin, ListView):
    template_name = "jobalerts/alert_list.html"
    context_object_name = "alerts"

    def get_queryset(self):
        return JobAlert.objects.filter(user=self.request.user).prefetch_related(
            "matches__job"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class OwnedAlertMixin(JobSeekerRequiredMixin):
    model = JobAlert
    template_name = "jobalerts/alert_form.html"

    def get_queryset(self):
        return JobAlert.objects.filter(user=self.request.user)


class JobAlertCreateView(OwnedAlertMixin, CreateView):
    form_class = JobAlertForm

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Your job alert has been created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("jobalerts:list")


class JobAlertUpdateView(OwnedAlertMixin, UpdateView):
    form_class = JobAlertForm

    def form_valid(self, form):
        messages.success(self.request, "Your job alert has been updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("jobalerts:list")


class JobAlertDeleteView(OwnedAlertMixin, DeleteView):
    template_name = "jobalerts/alert_confirm_delete.html"
    success_url = reverse_lazy("jobalerts:list")

    def form_valid(self, form):
        messages.success(self.request, "Your job alert has been deleted.")
        return super().form_valid(form)
