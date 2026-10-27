from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from core.mixins import EmployerRequiredMixin, JobSeekerRequiredMixin
from .forms import JobForm
from .models import Job, SavedJob

from django.core.paginator import Paginator
from django.views.generic import DetailView, ListView


class JobListView(ListView):
    model = Job
    template_name = "jobs/job_list.html"
    context_object_name = "jobs"
    paginate_by = 10

    POSTED_CHOICES = [
        ("", "Any time"),
        ("1", "Last 24 hours"),
        ("3", "Last 3 days"),
        ("7", "Last 7 days"),
        ("30", "Last 30 days"),
    ]

    def get_queryset(self):
        queryset = Job.objects.select_related("company").open()
        queryset = queryset.search(self.request.GET.get("q", "").strip())

        location = self.request.GET.get("location", "").strip()
        if location:
            queryset = queryset.filter(location__icontains=location)

        employment_type = self.request.GET.get("type", "")
        if employment_type in Job.EmploymentType.values:
            queryset = queryset.filter(employment_type=employment_type)

        experience_level = self.request.GET.get("level", "")
        if experience_level in Job.ExperienceLevel.values:
            queryset = queryset.filter(experience_level=experience_level)

        min_salary = self.request.GET.get("min_salary", "").strip()
        if min_salary.isdigit():
            min_salary = int(min_salary)
            queryset = queryset.filter(
                Q(salary_max__gte=min_salary) | Q(salary_min__gte=min_salary)
            )

        posted_days = {"1": 1, "3": 3, "7": 7, "30": 30}.get(
            self.request.GET.get("posted", "")
        )
        if posted_days:
            cutoff = timezone.now() - timedelta(days=posted_days)
            queryset = queryset.filter(created_at__gte=cutoff)

        sort = self.request.GET.get("sort", "newest")
        if sort == "oldest":
            queryset = queryset.order_by("created_at")
        else:
            queryset = queryset.order_by("-created_at")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["employment_types"] = Job.EmploymentType.choices
        context["experience_levels"] = Job.ExperienceLevel.choices
        context["posted_choices"] = self.POSTED_CHOICES
        context["current_filters"] = self.request.GET
        filters = self.request.GET
        active_values = (
            filters.get("q", "").strip(),
            filters.get("location", "").strip(),
            filters.get("type", "")
            if filters.get("type", "") in Job.EmploymentType.values
            else "",
            filters.get("level", "")
            if filters.get("level", "") in Job.ExperienceLevel.values
            else "",
            filters.get("min_salary", "")
            if filters.get("min_salary", "").isdigit()
            else "",
            filters.get("posted", "")
            if filters.get("posted", "") in {"1", "3", "7", "30"}
            else "",
        )
        context["active_filter_count"] = sum(bool(value) for value in active_values)

        user = self.request.user
        if user.is_authenticated and user.is_job_seeker:
            applicant = user.get_profile()
            saved_ids = set(
                SavedJob.objects.filter(
                    applicant=applicant, job__in=context["jobs"]
                ).values_list("job_id", flat=True)
            )
            for job in context["jobs"]:
                job.is_saved = job.pk in saved_ids

        return context


class JobDetailView(DetailView):
    template_name = "jobs/job_detail.html"
    context_object_name = "job"

    def get_queryset(self):
        return Job.objects.select_related("company").exclude(status=Job.Status.REMOVED)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated and user.is_job_seeker:
            from applications.models import Application  # local import avoids a circular import

            applicant = user.get_profile()
            context["has_applied"] = Application.objects.filter(
                job=self.object, applicant=applicant
            ).exists()
            context["is_saved"] = SavedJob.objects.filter(
                job=self.object, applicant=applicant
            ).exists()
        return context

@login_required
@require_POST
def toggle_save_job(request, pk):
    if not request.user.is_job_seeker:
        raise PermissionDenied

    job = get_object_or_404(Job.objects.exclude(status=Job.Status.REMOVED), pk=pk)
    applicant = request.user.get_profile()

    saved_job = SavedJob.objects.filter(applicant=applicant, job=job).first()
    if saved_job:
        saved_job.delete()
        messages.info(request, "Job removed from saved jobs.")
    else:
        SavedJob.objects.create(applicant=applicant, job=job)
        messages.success(request, "Job saved.")

    return redirect("jobs:detail", pk=job.pk)


class SavedJobsListView(JobSeekerRequiredMixin, ListView):
    template_name = "jobs/saved_jobs.html"
    context_object_name = "saved_jobs"

    def get_queryset(self):
        return (
            SavedJob.objects.filter(applicant=self.request.user.get_profile())
            .select_related("job", "job__company")
        )    

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
        if form.cleaned_data.get("status") == Job.Status.OPEN:
            form.instance.last_confirmed_at = timezone.now()
        messages.success(self.request, "Job updated.")
        return super().form_valid(form)


@login_required
@require_POST
def confirm_job_open(request, pk):
    if not request.user.is_employer:
        raise PermissionDenied

    company = getattr(request.user.get_profile(), "company", None)
    job = get_object_or_404(Job, pk=pk, company=company)
    if job.status != Job.Status.OPEN:
        messages.error(request, "Reopen this job before confirming it is still open.")
    else:
        job.last_confirmed_at = timezone.now()
        job.save(update_fields=["last_confirmed_at", "updated_at"])
        messages.success(request, "Job confirmed and visible to job seekers for 30 more days.")
    return redirect("jobs:employer_job_list")

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
