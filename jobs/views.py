from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.urls import reverse_lazy
from core.mixins import EmployerRequiredMixin

from .forms import JobForm
from .models import Job


class OwnerJobMixin(EmployerRequiredMixin):
    """Restrict create/edit/delete to jobs owned by the logged-in employer's company."""

    model = Job
    form_class = JobForm
    
    def get_queryset(self):
        # Combined with EmployerRequiredMixin, this is what stops one employer
        # from editing or deleting another employer's job: a mismatched pk
        # simply isn't in this queryset, so Django raises Http404, not 403.
        company = self.request.user.get_profile().company
        return Job.objects.filter(company=company)


class EmployerJobListView(EmployerRequiredMixin, ListView):
    model = Job
    template_name = "jobs/employer_job_list.html"
    context_object_name = "jobs"

    def get_queryset(self):
        company = self.request.user.get_profile().company
        return Job.objects.filter(company=company)


class JobCreateView(EmployerRequiredMixin, CreateView):
    model = Job
    form_class = JobForm
    template_name = "jobs/job_form.html"
    success_url = reverse_lazy("jobs:employer_job_list")

    def form_valid(self, form):
        form.instance.company = self.request.user.get_profile().company
        messages.success(self.request, "Job posted.")
        return super().form_valid(form)


class JobUpdateView(OwnerJobMixin, UpdateView):
    template_name = "jobs/job_form.html"
    success_url = reverse_lazy("jobs:employer_job_list")

    def form_valid(self, form):
        messages.success(self.request, "Job updated.")
        return super().form_valid(form)

class JobDeleteView(OwnerJobMixin, DeleteView):
    template_name = "jobs/job_confirm_delete.html"
    success_url = reverse_lazy("jobs:employer_job_list")

    def get_success_url(self):
        return "/employer/jobs/"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                request,
                "This job has applications and can't be deleted. Close it instead.",
            )
            return redirect("jobs:employer_job_list")
        messages.success(request, "Job deleted.")
        return redirect("jobs:employer_job_list")


def require_company(get_response):
    """Redirect employers with no company yet to create one first."""

    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_employer:
            has_company = hasattr(request.user.get_profile(), "company")
            if not has_company:
                messages.info(request, "Create your company profile before posting a job.")
                return redirect("companies:edit")
        return get_response(request, *args, **kwargs)

    return wrapper
