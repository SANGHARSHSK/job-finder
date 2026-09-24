import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from core.mixins import JobSeekerRequiredMixin
from jobs.models import Job

from .forms import ApplicationForm
from .models import Application


@login_required
def apply_to_job(request, pk):
    if not request.user.is_job_seeker:
        raise PermissionDenied

    job = get_object_or_404(Job.objects.exclude(status=Job.Status.REMOVED), pk=pk)
    applicant = request.user.get_profile()

    if not job.is_open:
        messages.error(request, "This job is no longer accepting applications.")
        return redirect("jobs:detail", pk=job.pk)

    if Application.objects.filter(job=job, applicant=applicant).exists():
        messages.info(request, "You've already applied to this job.")
        return redirect("jobs:detail", pk=job.pk)

    if request.method == "POST":
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.applicant = applicant
            try:
                application.save()
            except IntegrityError:
                # Safety net for the rare race: two near-simultaneous submits
                # from the same applicant. The check above catches the rest.
                messages.info(request, "You've already applied to this job.")
                return redirect("jobs:detail", pk=job.pk)
            messages.success(request, "Your application has been submitted.")
            return redirect("jobs:detail", pk=job.pk)
    else:
        form = ApplicationForm()

    return render(request, "applications/apply.html", {"form": form, "job": job})


@login_required
def resume_download(request, pk):
    application = get_object_or_404(Application, pk=pk)
    user = request.user

    is_applicant = user.is_job_seeker and application.applicant == user.get_profile()
    is_owning_employer = (
        user.is_employer
        and hasattr(user.get_profile(), "company")
        and application.job.company == user.get_profile().company
    )
    if not (is_applicant or is_owning_employer):
        raise PermissionDenied

    filename = f"{application.applicant.user.username}_resume{os.path.splitext(application.resume.name)[1]}"
    return FileResponse(
        application.resume.open("rb"), as_attachment=True, filename=filename
    )

class MyApplicationsListView(JobSeekerRequiredMixin, ListView):
    model = Application
    template_name = "applications/my_applications.html"
    context_object_name = "applications"

    def get_queryset(self):
        return (
            Application.objects.filter(applicant=self.request.user.get_profile())
            .select_related("job", "job__company")
        )


@login_required
@require_POST
def withdraw_application(request, pk):
    if not request.user.is_job_seeker:
        raise PermissionDenied

    # Filtering by applicant here, not just pk, is the ownership check: a
    # mismatched pk simply isn't in this queryset, so it 404s rather than
    # leaking whether someone else's application exists.
    application = get_object_or_404(
        Application, pk=pk, applicant=request.user.get_profile()
    )

    if not application.can_withdraw():
        messages.error(request, "This application can no longer be withdrawn.")
        return redirect("applications:my_applications")

    application.status = Application.Status.WITHDRAWN
    application.save(update_fields=["status", "updated_at"])
    messages.success(request, "Application withdrawn.")
    return redirect("applications:my_applications")