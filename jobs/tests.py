import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.test import override_settings
from applications.models import Application


from accounts.models import User
from companies.models import Company

from .models import Job

VALID_PASSWORD = "Str0ng-Pass-Phrase!"


def make_user(username, role):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=VALID_PASSWORD,
        role=role,
    )
    user.get_profile()
    return user


def make_employer(username="acme", with_company=True):
    employer = make_user(username, User.Role.EMPLOYER)
    if with_company:
        Company.objects.create(owner=employer.get_profile(), name=f"{username.title()} Inc")
    return employer


def make_seeker(username="alice"):
    return make_user(username, User.Role.JOB_SEEKER)


def make_job(employer, **overrides):
    data = {
        "title": "Backend Developer",
        "description": "Build things.",
        "location": "Remote",
        "employment_type": Job.EmploymentType.FULL_TIME,
        "experience_level": Job.ExperienceLevel.MID,
    }
    data.update(overrides)
    return Job.objects.create(company=employer.get_profile().company, **data)


class JobModelTests(TestCase):
    def test_string_representation(self):
        employer = make_employer("acme")
        job = make_job(employer, title="Backend Developer")
        self.assertEqual(str(job), "Backend Developer @ Acme Inc")

    def test_is_open_property(self):
        employer = make_employer()
        open_job = make_job(employer, status=Job.Status.OPEN)
        closed_job = make_job(employer, status=Job.Status.CLOSED)
        self.assertTrue(open_job.is_open)
        self.assertFalse(closed_job.is_open)

    def test_default_status_is_open(self):
        employer = make_employer()
        job = make_job(employer)
        self.assertEqual(job.status, Job.Status.OPEN)


class EmployerJobListViewTests(TestCase):
    def setUp(self):
        self.url = reverse("jobs:employer_job_list")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_job_seeker_gets_403(self):
        self.client.force_login(make_seeker())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_employer_only_sees_own_jobs(self):
        employer_a = make_employer("acme")
        employer_b = make_employer("beta")
        make_job(employer_a, title="Acme Job Listing")
        make_job(employer_b, title="Beta Job Listing")

        self.client.force_login(employer_a)
        response = self.client.get(self.url)

        self.assertContains(response, "Acme Job Listing")
        self.assertNotContains(response, "Beta Job Listing")

    def test_empty_state_message(self):
        self.client.force_login(make_employer())
        response = self.client.get(self.url)
        self.assertContains(response, "haven't posted any jobs")


class JobCreateViewTests(TestCase):
    def setUp(self):
        self.url = reverse("jobs:create")
        self.valid_data = {
            "title": "Backend Developer",
            "description": "Build things.",
            "requirements": "3+ years Python",
            "location": "Remote",
            "employment_type": Job.EmploymentType.FULL_TIME,
            "experience_level": Job.ExperienceLevel.MID,
            "salary_min": "60000",
            "salary_max": "90000",
            "status": Job.Status.OPEN,
        }

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_job_seeker_gets_403(self):
        self.client.force_login(make_seeker())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_employer_without_company_is_redirected_to_create_one(self):
        employer = make_employer(with_company=False)
        self.client.force_login(employer)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("companies:edit"))

    def test_employer_with_company_can_post_job(self):
        employer = make_employer()
        self.client.force_login(employer)
        response = self.client.post(self.url, self.valid_data)

        job = Job.objects.get(title="Backend Developer")
        self.assertRedirects(response, reverse("jobs:employer_job_list"))
        self.assertEqual(job.company, employer.get_profile().company)

    def test_salary_max_less_than_min_is_rejected(self):
        employer = make_employer()
        self.client.force_login(employer)
        data = dict(self.valid_data, salary_min="100000", salary_max="50000")

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "salary_max",
            "Maximum salary must not be less than minimum salary.",
        )
        self.assertFalse(Job.objects.filter(title="Backend Developer").exists())

    def test_company_field_cannot_be_submitted_by_client(self):
        employer_a = make_employer("acme")
        employer_b = make_employer("beta")
        self.client.force_login(employer_a)

        data = dict(self.valid_data, company=employer_b.get_profile().company.pk)
        self.client.post(self.url, data)

        job = Job.objects.get(title="Backend Developer")
        self.assertEqual(job.company, employer_a.get_profile().company)


class JobUpdateViewTests(TestCase):
    def setUp(self):
        self.employer = make_employer("acme")
        self.job = make_job(self.employer, title="Old Title")
        self.url = reverse("jobs:update", kwargs={"pk": self.job.pk})
        self.valid_data = {
            "title": "New Title",
            "description": "Updated description.",
            "requirements": "",
            "location": "Remote",
            "employment_type": Job.EmploymentType.FULL_TIME,
            "experience_level": Job.ExperienceLevel.MID,
            "status": Job.Status.OPEN,
        }

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_owner_can_update(self):
        self.client.force_login(self.employer)
        response = self.client.post(self.url, self.valid_data)

        self.assertRedirects(response, reverse("jobs:employer_job_list"))
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, "New Title")

    def test_other_employer_gets_404(self):
        other_employer = make_employer("beta")
        self.client.force_login(other_employer)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_other_employer_cannot_update_via_post(self):
        other_employer = make_employer("beta")
        self.client.force_login(other_employer)

        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, 404)
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, "Old Title")

    def test_job_seeker_gets_403(self):
        self.client.force_login(make_seeker())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)


class JobDeleteViewTests(TestCase):
    def setUp(self):
        self.employer = make_employer("acme")
        self.job = make_job(self.employer)
        self.url = reverse("jobs:delete", kwargs={"pk": self.job.pk})

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_owner_sees_confirmation_page(self):
        self.client.force_login(self.employer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.job.title)

    def test_owner_can_delete(self):
        self.client.force_login(self.employer)
        response = self.client.post(self.url)

        self.assertRedirects(response, reverse("jobs:employer_job_list"))
        self.assertFalse(Job.objects.filter(pk=self.job.pk).exists())

    def test_other_employer_gets_404(self):
        other_employer = make_employer("beta")
        self.client.force_login(other_employer)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Job.objects.filter(pk=self.job.pk).exists())

    def test_job_seeker_gets_403(self):
        self.client.force_login(make_seeker())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

class JobListViewTests(TestCase):
    def setUp(self):
        self.url = reverse("jobs:list")
        self.employer = make_employer("acme")
        self.other_employer = make_employer("beta")

    def test_anyone_can_view_job_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_only_open_jobs_are_listed(self):
        make_job(self.employer, title="Open Role", status=Job.Status.OPEN)
        make_job(self.employer, title="Closed Role", status=Job.Status.CLOSED)
        make_job(self.employer, title="Removed Role", status=Job.Status.REMOVED)

        response = self.client.get(self.url)

        self.assertContains(response, "Open Role")
        self.assertNotContains(response, "Closed Role")
        self.assertNotContains(response, "Removed Role")

    def test_search_by_title(self):
        make_job(self.employer, title="Backend Engineer")
        make_job(self.employer, title="Marketing Manager")

        response = self.client.get(self.url, {"q": "Backend"})

        self.assertContains(response, "Backend Engineer")
        self.assertNotContains(response, "Marketing Manager")

    def test_search_by_company_name(self):
        make_job(self.employer, title="Role A")
        make_job(self.other_employer, title="Role B")

        response = self.client.get(self.url, {"q": "Acme"})

        self.assertContains(response, "Role A")
        self.assertNotContains(response, "Role B")

    def test_filter_by_location(self):
        make_job(self.employer, title="Remote Role", location="Remote")
        make_job(self.employer, title="Onsite Role", location="Mumbai")

        response = self.client.get(self.url, {"location": "Remote"})

        self.assertContains(response, "Remote Role")
        self.assertNotContains(response, "Onsite Role")

    def test_filter_by_employment_type(self):
        make_job(self.employer, title="Full Time Role", employment_type=Job.EmploymentType.FULL_TIME)
        make_job(self.employer, title="Intern Role", employment_type=Job.EmploymentType.INTERNSHIP)

        response = self.client.get(self.url, {"type": Job.EmploymentType.INTERNSHIP})

        self.assertContains(response, "Intern Role")
        self.assertNotContains(response, "Full Time Role")

    def test_filter_by_experience_level(self):
        make_job(self.employer, title="Senior Role", experience_level=Job.ExperienceLevel.SENIOR)
        make_job(self.employer, title="Entry Role", experience_level=Job.ExperienceLevel.ENTRY)

        response = self.client.get(self.url, {"level": Job.ExperienceLevel.SENIOR})

        self.assertContains(response, "Senior Role")
        self.assertNotContains(response, "Entry Role")

    def test_invalid_filter_values_are_ignored_not_errored(self):
        make_job(self.employer, title="Normal Role")
        response = self.client.get(self.url, {"type": "not-a-real-type", "level": "also-fake"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Normal Role")

    def test_sort_newest_first_by_default(self):
        older = make_job(self.employer, title="Older Role")
        newer = make_job(self.employer, title="Newer Role")

        response = self.client.get(self.url)

        positions = response.content.decode()
        self.assertLess(positions.index("Newer Role"), positions.index("Older Role"))

    def test_sort_oldest_first(self):
        make_job(self.employer, title="Older Role")
        make_job(self.employer, title="Newer Role")

        response = self.client.get(self.url, {"sort": "oldest"})

        positions = response.content.decode()
        self.assertLess(positions.index("Older Role"), positions.index("Newer Role"))

    def test_pagination_limits_results_per_page(self):
        for i in range(15):
            make_job(self.employer, title=f"Role {i}")

        response = self.client.get(self.url)

        self.assertEqual(len(response.context["jobs"]), 10)
        self.assertTrue(response.context["is_paginated"])


class JobDetailViewTests(TestCase):
    def setUp(self):
        self.employer = make_employer("acme")

    def test_open_job_is_visible(self):
        job = make_job(self.employer, title="Open Role", status=Job.Status.OPEN)
        response = self.client.get(reverse("jobs:detail", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open Role")

    def test_closed_job_is_still_reachable_directly(self):
        job = make_job(self.employer, title="Closed Role", status=Job.Status.CLOSED)
        response = self.client.get(reverse("jobs:detail", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no longer accepting applications")

    def test_removed_job_returns_404(self):
        job = make_job(self.employer, title="Removed Role", status=Job.Status.REMOVED)
        response = self.client.get(reverse("jobs:detail", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_job_returns_404(self):
        response = self.client.get(reverse("jobs:detail", kwargs={"pk": 9999}))
        self.assertEqual(response.status_code, 404)

    def test_no_login_required(self):
        job = make_job(self.employer, title="Public Role")
        response = self.client.get(reverse("jobs:detail", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 200)   


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class JobDeleteWithApplicationsTests(TestCase):
    def test_job_with_applications_cannot_be_deleted(self):
        employer = make_employer("acme")
        job = make_job(employer)
        seeker = User.objects.create_user(
            "carol", "carol@example.com", VALID_PASSWORD, role=User.Role.JOB_SEEKER
        )
        seeker.get_profile()
        Application.objects.create(
            job=job,
            applicant=seeker.get_profile(),
            resume=SimpleUploadedFile("resume.pdf", b"%PDF-1.4 x", content_type="application/pdf"),
        )

        self.client.force_login(employer)
        response = self.client.post(reverse("jobs:delete", kwargs={"pk": job.pk}), follow=True)

        self.assertRedirects(response, reverse("jobs:employer_job_list"))
        self.assertContains(response, "can&#x27;t be deleted")
        self.assertTrue(Job.objects.filter(pk=job.pk).exists())
             