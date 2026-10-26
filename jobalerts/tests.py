from django.core import mail
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from accounts.models import User

from .models import ExternalJob, JobAlert, JobAlertMatch
from .services import email_matches, sync_alert


def make_user(username):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="SafePassword!293",
        role=User.Role.JOB_SEEKER,
    )


def make_alert(user, **overrides):
    values = {
        "role_title": "Python Developer",
        "role_description": "Build backend web services",
        "skills": "Python, Django",
        "location": "Bengaluru",
    }
    values.update(overrides)
    return JobAlert.objects.create(user=user, **values)


def provider_job(**overrides):
    values = {
        "id": 1001,
        "title": "Python Developer",
        "company": "Example Labs",
        "location": "Bengaluru",
        "snippet": "Build Python and Django backend services.",
        "salary": "₹8,00,000 - ₹12,00,000",
        "type": "Full-time",
        "source": "Example careers",
        "link": "https://jooble.org/jdp/1001",
        "updated": "2026-10-26T12:00:00Z",
    }
    values.update(overrides)
    return values


class FakeProvider:
    provider_id = "jooble"

    def __init__(self, jobs):
        self.jobs = jobs

    def search(self, alert):
        return self.jobs


class JobAlertMatchingTests(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.alert = make_alert(self.user)

    def test_sync_saves_a_relevant_job_and_explains_match(self):
        new_matches = sync_alert(self.alert, FakeProvider([provider_job()]))

        self.assertEqual(len(new_matches), 1)
        match = JobAlertMatch.objects.select_related("job").get()
        self.assertEqual(match.job.title, "Python Developer")
        self.assertGreaterEqual(match.score, 90)
        self.assertIn("Skills: Python, Django", match.match_reasons)
        self.assertEqual(match.job.source_name, "Example careers")

    def test_sync_deduplicates_repeated_provider_results(self):
        provider = FakeProvider([provider_job()])

        self.assertEqual(len(sync_alert(self.alert, provider)), 1)
        self.assertEqual(sync_alert(self.alert, provider), [])
        self.assertEqual(ExternalJob.objects.count(), 1)
        self.assertEqual(JobAlertMatch.objects.count(), 1)

    def test_sync_skips_nonmatching_employment_type_and_invalid_links(self):
        provider = FakeProvider(
            [
                provider_job(id=1002, type="Contract"),
                provider_job(id=1004, type=""),
                provider_job(id=1003, link="javascript:alert(1)"),
            ]
        )
        self.alert.employment_type = JobAlert.EmploymentType.FULL_TIME
        self.alert.save(update_fields=["employment_type", "updated_at"])

        self.assertEqual(sync_alert(self.alert, provider), [])
        self.assertEqual(ExternalJob.objects.count(), 0)

    def test_remote_only_alert_skips_nonremote_listings(self):
        self.alert.remote_only = True
        self.alert.save(update_fields=["remote_only", "updated_at"])
        local_provider = FakeProvider([provider_job(id=1005)])
        remote_provider = FakeProvider(
            [provider_job(id=1006, location="Remote, India", snippet="Remote Python and Django role")]
        )

        self.assertEqual(sync_alert(self.alert, local_provider), [])
        self.assertEqual(len(sync_alert(self.alert, remote_provider)), 1)

    def test_sync_updates_existing_job_without_creating_a_second_match(self):
        provider = FakeProvider([provider_job()])
        sync_alert(self.alert, provider)
        provider.jobs = [provider_job(snippet="Updated Python and Django role")]

        self.assertEqual(sync_alert(self.alert, provider), [])
        self.assertEqual(ExternalJob.objects.count(), 1)
        self.assertEqual(ExternalJob.objects.get().snippet, "Updated Python and Django role")
        self.assertEqual(JobAlertMatch.objects.count(), 1)

    def test_email_marks_matches_sent_after_delivery(self):
        match = sync_alert(self.alert, FakeProvider([provider_job()]))[0]
        self.alert.email_enabled = True
        self.alert.save(update_fields=["email_enabled", "updated_at"])

        self.assertTrue(email_matches(self.alert, [match]))
        self.assertEqual(len(mail.outbox), 1)
        match.refresh_from_db()
        self.assertIsNotNone(match.email_sent_at)

    @patch("jobalerts.services.send_mail", side_effect=OSError("mail server unavailable"))
    def test_email_failure_leaves_match_pending_for_retry(self, mocked_send_mail):
        match = sync_alert(self.alert, FakeProvider([provider_job()]))[0]
        self.alert.email_enabled = True
        self.alert.save(update_fields=["email_enabled", "updated_at"])

        self.assertFalse(email_matches(self.alert, [match]))
        match.refresh_from_db()
        self.assertIsNone(match.email_sent_at)
        mocked_send_mail.assert_called_once()


class JobAlertViewTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner")
        self.other_user = make_user("other")
        self.alert = make_alert(self.owner)

    def test_alert_crud_is_scoped_to_the_logged_in_job_seeker(self):
        self.client.force_login(self.other_user)
        response = self.client.get(
            reverse("jobalerts:update", kwargs={"pk": self.alert.pk})
        )
        self.assertEqual(response.status_code, 404)

        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("jobalerts:update", kwargs={"pk": self.alert.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_external_results_only_show_jobs_matched_to_the_current_user(self):
        visible_job = ExternalJob.objects.create(
            provider_id="visible",
            title="Python Developer",
            source_url="https://jooble.org/jdp/visible",
        )
        hidden_job = ExternalJob.objects.create(
            provider_id="hidden",
            title="Private match",
            source_url="https://jooble.org/jdp/hidden",
        )
        JobAlertMatch.objects.create(alert=self.alert, job=visible_job, score=90)
        other_alert = make_alert(self.other_user)
        JobAlertMatch.objects.create(alert=other_alert, job=hidden_job, score=90)

        self.client.force_login(self.owner)
        response = self.client.get(reverse("jobalerts:external_jobs"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Developer")
        self.assertNotContains(response, "Private match")

    def test_anonymous_external_job_requests_redirect_to_login(self):
        response = self.client.get(reverse("jobalerts:external_jobs"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_alert_list_renders_saved_matches(self):
        job = ExternalJob.objects.create(
            provider_id="listed",
            title="Python Developer",
            company="Example Labs",
            snippet="Python and Django role",
            source_url="https://jooble.org/jdp/listed",
        )
        JobAlertMatch.objects.create(
            alert=self.alert,
            job=job,
            score=90,
            match_reasons=["Skills: Python, Django"],
        )
        self.client.force_login(self.owner)

        response = self.client.get(reverse("jobalerts:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recent matches")
        self.assertContains(response, "Python Developer")
        self.assertContains(response, "Skills: Python, Django")

    def test_alert_create_form_saves_preferences(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("jobalerts:create"),
            {
                "role_title": "Backend Engineer",
                "role_description": "Build reliable web services",
                "skills": "Python, PostgreSQL",
                "location": "Pune",
                "remote_only": "on",
                "employment_type": JobAlert.EmploymentType.FULL_TIME,
                "min_salary": "1200000",
                "frequency": JobAlert.Frequency.DAILY,
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("jobalerts:list"))
        alert = JobAlert.objects.get(role_title="Backend Engineer")
        self.assertEqual(alert.user, self.owner)
        self.assertTrue(alert.remote_only)
        self.assertEqual(alert.min_salary, 1200000)
        self.assertFalse(alert.email_enabled)

    def test_alert_delete_requires_owner_confirmation(self):
        self.client.force_login(self.owner)
        url = reverse("jobalerts:delete", kwargs={"pk": self.alert.pk})

        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url)

        self.assertRedirects(response, reverse("jobalerts:list"))
        self.assertFalse(JobAlert.objects.filter(pk=self.alert.pk).exists())
