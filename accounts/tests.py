from django.test import TestCase
from django.urls import reverse

from .models import EmployerProfile, JobSeekerProfile, User

VALID_PASSWORD = "Str0ng-Pass-Phrase!"


def registration_data(**overrides):
    data = {
        "username": "alice",
        "first_name": "Alice",
        "last_name": "Doe",
        "email": "alice@example.com",
        "role": User.Role.JOB_SEEKER,
        "password1": VALID_PASSWORD,
        "password2": VALID_PASSWORD,
    }
    data.update(overrides)
    return data


class UserModelTests(TestCase):
    def test_role_helper_properties(self):
        seeker = User(role=User.Role.JOB_SEEKER)
        employer = User(role=User.Role.EMPLOYER)
        no_role = User()

        self.assertTrue(seeker.is_job_seeker)
        self.assertFalse(seeker.is_employer)
        self.assertTrue(employer.is_employer)
        self.assertFalse(employer.is_job_seeker)
        self.assertFalse(no_role.is_job_seeker or no_role.is_employer)


class RegistrationTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:register")

    def test_registration_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_job_seeker_registration_creates_user_and_profile(self):
        response = self.client.post(self.url, registration_data())

        self.assertRedirects(response, reverse("core:home"))
        user = User.objects.get(username="alice")
        self.assertEqual(user.role, User.Role.JOB_SEEKER)
        self.assertTrue(JobSeekerProfile.objects.filter(user=user).exists())
        self.assertFalse(EmployerProfile.objects.filter(user=user).exists())

    def test_password_is_hashed(self):
        self.client.post(self.url, registration_data())
        user = User.objects.get(username="alice")

        self.assertNotEqual(user.password, VALID_PASSWORD)
        self.assertTrue(user.check_password(VALID_PASSWORD))

    def test_employer_registration_creates_employer_profile(self):
        data = registration_data(
            username="acme", email="hr@acme.com", role=User.Role.EMPLOYER
        )
        self.client.post(self.url, data)

        user = User.objects.get(username="acme")
        self.assertEqual(user.role, User.Role.EMPLOYER)
        self.assertTrue(EmployerProfile.objects.filter(user=user).exists())
        self.assertFalse(JobSeekerProfile.objects.filter(user=user).exists())

    def test_user_is_logged_in_after_registration(self):
        self.client.post(self.url, registration_data())
        response = self.client.get(reverse("core:home"))
        self.assertTrue(response.context["user"].is_authenticated)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(
            username="existing", email="Alice@Example.com", password=VALID_PASSWORD
        )
        response = self.client.post(self.url, registration_data())

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "An account with this email already exists.",
        )
        self.assertEqual(User.objects.count(), 1)

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            self.url, registration_data(password2="Different-Pass-123!")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="alice").exists())

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            self.url, registration_data(password1="12345678", password2="12345678")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="alice").exists())

    def test_invalid_role_is_rejected(self):
        response = self.client.post(self.url, registration_data(role="admin"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="alice").exists())

    def test_authenticated_user_is_redirected_away_from_register(self):
        user = User.objects.create_user(
            username="bob", email="bob@example.com", password=VALID_PASSWORD
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("core:home"))


class LoginLogoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="alice", email="alice@example.com", password=VALID_PASSWORD
        )

    def test_login_with_valid_credentials(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "alice", "password": VALID_PASSWORD},
        )
        self.assertRedirects(response, reverse("core:home"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "alice", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_rejects_get_requests(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_via_post_ends_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("core:home"))
        self.assertNotIn("_auth_user_id", self.client.session)