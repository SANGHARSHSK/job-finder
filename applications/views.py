import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

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