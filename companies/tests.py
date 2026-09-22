from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Company

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


def make_employer(username="acme"):
    return make_user(username, User.Role.EMPLOYER)


def make_seeker(username="alice"):
    return make_user(username, User.Role.JOB_SEEKER)


class CompanyModelTests(TestCase):
    def test_string_representation_is_name(self):
        employer = make_employer()
        company = Company.objects.create(owner=employer.get_profile(), name="Acme Inc")
        self.assertEqual(str(company), "Acme Inc")

    def test_get_absolute_url(self):
        employer = make_employer()
        company = Company.objects.create(owner=employer.get_profile(), name="Acme Inc")
        self.assertEqual(
            company.get_absolute_url(), reverse("companies:detail", kwargs={"pk": company.pk})
        )


class CompanyEditViewTests(TestCase):
    def setUp(self):
        self.url = reverse("companies:edit")
        self.valid_data = {
            "name": "Acme Inc",
            "description": "We build things.",
            "website": "https://acme.example.com",
            "location": "Remote",
            "industry": "Software",
            "company_size": Company.CompanySize.SMALL,
        }

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_job_seeker_gets_403(self):
        self.client.force_login(make_seeker())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_employer_can_create_company(self):
        employer = make_employer()
        self.client.force_login(employer)
        response = self.client.post(self.url, self.valid_data)

        company = Company.objects.get(owner=employer.get_profile())
        self.assertRedirects(response, reverse("companies:detail", kwargs={"pk": company.pk}))
        self.assertEqual(company.name, "Acme Inc")

    def test_employer_can_edit_existing_company(self):
        employer = make_employer()
        Company.objects.create(owner=employer.get_profile(), name="Old Name")
        self.client.force_login(employer)

        data = dict(self.valid_data, name="New Name")
        self.client.post(self.url, data)

        company = Company.objects.get(owner=employer.get_profile())
        self.assertEqual(company.name, "New Name")
        self.assertEqual(Company.objects.filter(owner=employer.get_profile()).count(), 1)

    def test_get_prefills_existing_company(self):
        employer = make_employer()
        Company.objects.create(owner=employer.get_profile(), name="Acme Inc")
        self.client.force_login(employer)

        response = self.client.get(self.url)
        self.assertContains(response, "Acme Inc")

    def test_editing_does_not_create_a_second_company(self):
        employer_a = make_employer("acme")
        employer_b = make_employer("beta")
        Company.objects.create(owner=employer_a.get_profile(), name="Acme Inc")
        Company.objects.create(owner=employer_b.get_profile(), name="Beta LLC")

        self.client.force_login(employer_a)
        self.client.post(self.url, dict(self.valid_data, name="Acme Renamed"))

        self.assertEqual(Company.objects.count(), 2)
        self.assertEqual(
            Company.objects.get(owner=employer_a.get_profile()).name, "Acme Renamed"
        )
        self.assertEqual(
            Company.objects.get(owner=employer_b.get_profile()).name, "Beta LLC"
        )

    def test_invalid_website_is_rejected(self):
        employer = make_employer()
        self.client.force_login(employer)

        response = self.client.post(self.url, dict(self.valid_data, website="not-a-url"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Company.objects.filter(owner=employer.get_profile()).exists())


class CompanyDetailViewTests(TestCase):
    def setUp(self):
        self.employer = make_employer()
        self.company = Company.objects.create(
            owner=self.employer.get_profile(), name="Acme Inc", location="Remote"
        )
        self.url = reverse("companies:detail", kwargs={"pk": self.company.pk})

    def test_anyone_can_view_company_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acme Inc")

    def test_unauthenticated_visitor_does_not_see_edit_link(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "Edit this company")

    def test_owner_sees_edit_link(self):
        self.client.force_login(self.employer)
        response = self.client.get(self.url)
        self.assertContains(response, "Edit this company")

    def test_other_employer_does_not_see_edit_link(self):
        self.client.force_login(make_employer("beta"))
        response = self.client.get(self.url)
        self.assertContains(response, "Acme Inc")
        self.assertNotContains(response, "Edit this company")

    def test_job_seeker_does_not_see_edit_link(self):
        self.client.force_login(make_seeker())
        response = self.client.get(self.url)
        self.assertNotContains(response, "Edit this company")

    def test_missing_company_returns_404(self):
        response = self.client.get(reverse("companies:detail", kwargs={"pk": 9999}))
        self.assertEqual(response.status_code, 404)