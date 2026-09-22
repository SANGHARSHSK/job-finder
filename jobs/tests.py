from django.test import TestCase
from django.urls import reverse

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