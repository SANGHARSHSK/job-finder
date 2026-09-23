import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from companies.models import Company
from jobs.models import Job

from .models import Application

VALID_PASSWORD = "Str0ng-Pass-Phrase!"
MEDIA_ROOT = tempfile.mkdtemp()


def make_user(username, role):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=VALID_PASSWORD,
        role=role,
    )
    user.get_profile()
    return user


def make_employer(username="acme"):
    employer = make_user(username, User.Role.EMPLOYER)
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


def pdf_file(name="resume.pdf", content=b"%PDF-1.4 fake resume content"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ApplicationModelTests(TestCase):
    def test_string_representation(self):
        employer = make_employer()
        seeker = make_seeker()
        job = make_job(employer)
        application = Application.objects.create(
            job=job, applicant=seeker.get_profile(), resume=pdf_file()
        )
        self.assertEqual(str(application), "alice -> Backend Developer")

    def test_duplicate_application_is_rejected_at_database_level(self):
        employer = make_employer()
        seeker = make_seeker()
        job = make_job(employer)
        Application.objects.create(job=job, applicant=seeker.get_profile(), resume=pdf_file())

        with self.assertRaises(Exception):
            Application.objects.create(job=job, applicant=seeker.get_profile(), resume=pdf_file())

    def test_can_withdraw_only_while_applied_or_under_review(self):
        employer = make_employer()
        seeker = make_seeker()
        job = make_job(employer)
        application = Application.objects.create(
            job=job, applicant=seeker.get_profile(), resume=pdf_file(),
            status=Application.Status.SHORTLISTED,
        )
        self.assertFalse(application.can_withdraw())

        application.status = Application.Status.APPLIED
        self.assertTrue(application.can_withdraw())

    def test_employer_transition_rules(self):
        employer = make_employer()
        seeker = make_seeker()
        job = make_job(employer)
        application = Application.objects.create(
            job=job, applicant=seeker.get_profile(), resume=pdf_file()
        )
        self.assertTrue(application.can_employer_transition_to(Application.Status.SHORTLISTED))
        self.assertFalse(application.can_employer_transition_to(Application.Status.REJECTED) is False)
        # A rejected application can't move anywhere else.
        application.status = Application.Status.REJECTED
        self.assertFalse(application.can_employer_transition_to(Application.Status.HIRED))


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ApplyViewTests(TestCase):
    def setUp(self):
        self.employer = make_employer()
        self.job = make_job(self.employer)
        self.url = reverse("applications:apply", kwargs={"pk": self.job.pk})

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_employer_cannot_apply(self):
        self.client.force_login(make_employer("beta"))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_job_seeker_can_apply(self):
        seeker = make_seeker()
        self.client.force_login(seeker)

        response = self.client.post(
            self.url, {"resume": pdf_file(), "cover_letter": "I'd love this role."}
        )

        self.assertRedirects(response, reverse("jobs:detail", kwargs={"pk": self.job.pk}))
        application = Application.objects.get(job=self.job, applicant=seeker.get_profile())
        self.assertEqual(application.status, Application.Status.APPLIED)
        self.assertEqual(application.cover_letter, "I'd love this role.")

    def test_cover_letter_is_optional(self):
        seeker = make_seeker()
        self.client.force_login(seeker)

        response = self.client.post(self.url, {"resume": pdf_file()})

        self.assertRedirects(response, reverse("jobs:detail", kwargs={"pk": self.job.pk}))
        self.assertTrue(Application.objects.filter(job=self.job, applicant=seeker.get_profile()).exists())

    def test_duplicate_application_is_blocked_with_message(self):
        seeker = make_seeker()
        Application.objects.create(job=self.job, applicant=seeker.get_profile(), resume=pdf_file())
        self.client.force_login(seeker)

        response = self.client.get(self.url, follow=True)

        self.assertRedirects(response, reverse("jobs:detail", kwargs={"pk": self.job.pk}))
        self.assertEqual(Application.objects.filter(job=self.job, applicant=seeker.get_profile()).count(), 1)

    def test_cannot_apply_to_closed_job(self):
        self.job.status = Job.Status.CLOSED
        self.job.save()
        seeker = make_seeker()
        self.client.force_login(seeker)

        response = self.client.get(self.url, follow=True)

        self.assertRedirects(response, reverse("jobs:detail", kwargs={"pk": self.job.pk}))
        self.assertFalse(Application.objects.filter(job=self.job).exists())

    def test_disallowed_file_extension_is_rejected(self):
        seeker = make_seeker()
        self.client.force_login(seeker)
        bad_file = SimpleUploadedFile("resume.exe", b"not a real resume", content_type="application/octet-stream")

        response = self.client.post(self.url, {"resume": bad_file})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Application.objects.filter(job=self.job).exists())

    def test_oversized_file_is_rejected(self):
        seeker = make_seeker()
        self.client.force_login(seeker)
        big_file = SimpleUploadedFile(
            "resume.pdf", b"x" * (6 * 1024 * 1024), content_type="application/pdf"
        )

        response = self.client.post(self.url, {"resume": big_file})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Application.objects.filter(job=self.job).exists())

    def test_missing_resume_is_rejected(self):
        seeker = make_seeker()
        self.client.force_login(seeker)

        response = self.client.post(self.url, {"cover_letter": "No resume attached."})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Application.objects.filter(job=self.job).exists())


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ResumeDownloadViewTests(TestCase):
    def setUp(self):
        self.employer = make_employer("acme")
        self.other_employer = make_employer("beta")
        self.seeker = make_seeker()
        self.other_seeker = make_seeker("bob")
        self.job = make_job(self.employer)
        self.application = Application.objects.create(
            job=self.job, applicant=self.seeker.get_profile(), resume=pdf_file()
        )
        self.url = reverse("applications:resume_download", kwargs={"pk": self.application.pk})

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_applicant_can_download_own_resume(self):
        self.client.force_login(self.seeker)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_owning_employer_can_download(self):
        self.client.force_login(self.employer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_other_seeker_is_denied(self):
        self.client.force_login(self.other_seeker)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_unrelated_employer_is_denied(self):
        self.client.force_login(self.other_employer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)