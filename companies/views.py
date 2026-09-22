from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView

from core.mixins import EmployerRequiredMixin

from .forms import CompanyForm
from .models import Company
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


class CompanyDetailView(DetailView):
    model = Company
    template_name = "companies/company_detail.html"
    context_object_name = "company"


@login_required
def company_edit(request):
    # Wrapping this in a class-based view buys little here; a function reads
    # more clearly for a single create-or-edit form tied to request.user.
    if not request.user.is_employer:
        raise PermissionDenied

    employer_profile = request.user.get_profile()
    company = Company.objects.filter(owner=employer_profile).first()

    if request.method == "POST":
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            new_company = form.save(commit=False)
            new_company.owner = employer_profile
            new_company.save()
            messages.success(request, "Your company profile has been saved.")
            return redirect("companies:detail", pk=new_company.pk)
    else:
        form = CompanyForm(instance=company)

    return render(request, "companies/company_form.html", {"form": form, "company": company})