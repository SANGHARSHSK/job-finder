from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.views import View

from accounts.models import User

from .mixins import EmployerRequiredMixin, JobSeekerRequiredMixin


class SeekerOnlyView(JobSeekerRequiredMixin, View):
    def get(self, request):
        return HttpResponse("ok")


class EmployerOnlyView(EmployerRequiredMixin, View):
    def get(self, request):
        return HttpResponse("ok")


class RoleMixinTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seeker = User.objects.create_user(
            "seeker", "seeker@example.com", "Str0ng-Pass-Phrase!",
            role=User.Role.JOB_SEEKER,
        )
        cls.employer = User.objects.create_user(
            "employer", "employer@example.com", "Str0ng-Pass-Phrase!",
            role=User.Role.EMPLOYER,
        )
        cls.superuser = User.objects.create_superuser(
            "admin", "admin@example.com", "Str0ng-Pass-Phrase!",
        )

    def call(self, view_class, user):
        request = RequestFactory().get("/protected/")
        request.user = user
        return view_class.as_view()(request)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.call(SeekerOnlyView, AnonymousUser())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("accounts:login")))

    def test_job_seeker_can_access_job_seeker_view(self):
        self.assertEqual(self.call(SeekerOnlyView, self.seeker).status_code, 200)

    def test_employer_is_denied_on_job_seeker_view(self):
        with self.assertRaises(PermissionDenied):
            self.call(SeekerOnlyView, self.employer)

    def test_employer_can_access_employer_view(self):
        self.assertEqual(self.call(EmployerOnlyView, self.employer).status_code, 200)

    def test_job_seeker_is_denied_on_employer_view(self):
        with self.assertRaises(PermissionDenied):
            self.call(EmployerOnlyView, self.seeker)

    def test_user_without_role_is_denied_on_both_views(self):
        with self.assertRaises(PermissionDenied):
            self.call(SeekerOnlyView, self.superuser)
        with self.assertRaises(PermissionDenied):
            self.call(EmployerOnlyView, self.superuser)