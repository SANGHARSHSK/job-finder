import re
from urllib.parse import urlparse

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import EmployerProfile, JobSeekerProfile, User

VALID_PASSWORD = "Str0ng-Pass-Phrase!"
NEW_PASSWORD = "An0ther-Str0ng-Pass!"


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

    def make_user(username="alice", role=User.Role.JOB_SEEKER, **extra):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=VALID_PASSWORD,
            role=role,
            **extra,
        )
        user.get_profile()
        return user


        class GetProfileTests(TestCase):
            def test_returns_matching_profile_for_each_role(self):
                seeker = make_user("seeker", User.Role.JOB_SEEKER)
                employer = make_user("employer", User.Role.EMPLOYER)

                self.assertIsInstance(seeker.get_profile(), JobSeekerProfile)
                self.assertIsInstance(employer.get_profile(), EmployerProfile)

            def test_creates_missing_profile(self):
                user = User.objects.create_user(
                    "bob", "bob@example.com", VALID_PASSWORD, role=User.Role.EMPLOYER
                )
                self.assertFalse(EmployerProfile.objects.filter(user=user).exists())

                user.get_profile()

                self.assertTrue(EmployerProfile.objects.filter(user=user).exists())

            def test_returns_none_for_user_without_role(self):
                admin = User.objects.create_superuser("admin", "admin@example.com", VALID_PASSWORD)
                self.assertIsNone(admin.get_profile())


        class ProfileViewTests(TestCase):
            def test_profile_requires_login(self):
                url = reverse("accounts:profile")
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

            def test_user_can_view_own_profile(self):
                self.client.force_login(make_user())
                response = self.client.get(reverse("accounts:profile"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "alice@example.com")

            def test_user_without_role_can_view_profile_page(self):
                admin = User.objects.create_superuser("admin", "admin@example.com", VALID_PASSWORD)
                self.client.force_login(admin)
                response = self.client.get(reverse("accounts:profile"))
                self.assertEqual(response.status_code, 200)


        class ProfileEditTests(TestCase):
            def setUp(self):
                self.url = reverse("accounts:profile_edit")

            def test_edit_requires_login(self):
                response = self.client.get(self.url)
                self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

            def test_job_seeker_can_update_profile(self):
                user = make_user()
                self.client.force_login(user)
                response = self.client.post(
                    self.url,
                    {
                        "first_name": "Alicia",
                        "last_name": "Doe",
                        "email": "alicia@example.com",
                        "phone": "+1 555 123 4567",
                        "location": "Pune",
                        "headline": "Python developer",
                        "bio": "",
                        "skills": "Python, Django",
                    },
                )

                self.assertRedirects(response, reverse("accounts:profile"))
                user.refresh_from_db()
                profile = JobSeekerProfile.objects.get(user=user)
                self.assertEqual(user.first_name, "Alicia")
                self.assertEqual(user.email, "alicia@example.com")
                self.assertEqual(profile.location, "Pune")
                self.assertEqual(profile.skills, "Python, Django")

            def test_employer_can_update_profile(self):
                user = make_user("acme", User.Role.EMPLOYER)
                self.client.force_login(user)
                response = self.client.post(
                    self.url,
                    {
                        "first_name": "Ann",
                        "last_name": "Recruiter",
                        "email": "acme@example.com",
                        "job_title": "Talent Lead",
                        "phone": "+1 555 000 1111",
                    },
                )

                self.assertRedirects(response, reverse("accounts:profile"))
                profile = EmployerProfile.objects.get(user=user)
                self.assertEqual(profile.job_title, "Talent Lead")

            def test_email_of_another_user_is_rejected(self):
                make_user("alice")
                bob = make_user("bob")
                self.client.force_login(bob)
                response = self.client.post(
                    self.url,
                    {"first_name": "Bob", "last_name": "B", "email": "alice@example.com"},
                )

                self.assertEqual(response.status_code, 200)
                self.assertFormError(
                    response.context["user_form"],
                    "email",
                    "An account with this email already exists.",
                )
                bob.refresh_from_db()
                self.assertEqual(bob.email, "bob@example.com")

            def test_keeping_own_email_is_allowed(self):
                user = make_user()
                self.client.force_login(user)
                response = self.client.post(
                    self.url,
                    {"first_name": "Alice", "last_name": "Doe", "email": "alice@example.com"},
                )
                self.assertRedirects(response, reverse("accounts:profile"))

            def test_invalid_phone_is_rejected(self):
                user = make_user()
                self.client.force_login(user)
                response = self.client.post(
                    self.url,
                    {
                        "first_name": "Alice",
                        "last_name": "Doe",
                        "email": "alice@example.com",
                        "phone": "abc",
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertFormError(
                    response.context["profile_form"], "phone", "Enter a valid phone number."
                )
                self.assertEqual(JobSeekerProfile.objects.get(user=user).phone, "")

            def test_user_without_role_gets_403(self):
                admin = User.objects.create_superuser("admin", "admin@example.com", VALID_PASSWORD)
                self.client.force_login(admin)
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 403)

            def test_missing_profile_is_created_on_demand(self):
                user = User.objects.create_user(
                    "carol", "carol@example.com", VALID_PASSWORD, role=User.Role.EMPLOYER
                )
                self.client.force_login(user)
                response = self.client.get(self.url)

                self.assertEqual(response.status_code, 200)
                self.assertTrue(EmployerProfile.objects.filter(user=user).exists())


        class PasswordChangeTests(TestCase):
            def setUp(self):
                self.user = make_user()
                self.url = reverse("accounts:password_change")

            def test_requires_login(self):
                response = self.client.get(self.url)
                self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

            def test_password_can_be_changed(self):
                self.client.force_login(self.user)
                response = self.client.post(
                    self.url,
                    {
                        "old_password": VALID_PASSWORD,
                        "new_password1": NEW_PASSWORD,
                        "new_password2": NEW_PASSWORD,
                    },
                )

                self.assertRedirects(response, reverse("accounts:profile"))
                self.user.refresh_from_db()
                self.assertTrue(self.user.check_password(NEW_PASSWORD))

            def test_wrong_old_password_is_rejected(self):
                self.client.force_login(self.user)
                response = self.client.post(
                    self.url,
                    {
                        "old_password": "not-my-password",
                        "new_password1": NEW_PASSWORD,
                        "new_password2": NEW_PASSWORD,
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.user.refresh_from_db()
                self.assertTrue(self.user.check_password(VALID_PASSWORD))


        class PasswordResetTests(TestCase):
            def setUp(self):
                self.user = make_user()
                self.url = reverse("accounts:password_reset")

            def test_reset_request_sends_email_with_link(self):
                response = self.client.post(self.url, {"email": "alice@example.com"})

                self.assertRedirects(response, reverse("accounts:password_reset_done"))
                self.assertEqual(len(mail.outbox), 1)
                self.assertEqual(mail.outbox[0].to, ["alice@example.com"])
                self.assertIn("/accounts/reset/", mail.outbox[0].body)

            def test_unknown_email_gets_same_response_and_sends_nothing(self):
                response = self.client.post(self.url, {"email": "nobody@example.com"})

                self.assertRedirects(response, reverse("accounts:password_reset_done"))
                self.assertEqual(len(mail.outbox), 0)

            def test_full_reset_flow_changes_password(self):
                self.client.post(self.url, {"email": "alice@example.com"})
                link = re.search(r"https?://\S+", mail.outbox[0].body).group(0)

                response = self.client.get(urlparse(link).path, follow=True)
                self.assertTrue(response.context["validlink"])

                set_password_url = response.redirect_chain[-1][0]
                response = self.client.post(
                    set_password_url,
                    {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
                )

                self.assertRedirects(response, reverse("accounts:password_reset_complete"))
                self.user.refresh_from_db()
                self.assertTrue(self.user.check_password(NEW_PASSWORD))

            def test_invalid_link_is_rejected(self):
                url = reverse(
                    "accounts:password_reset_confirm",
                    kwargs={"uidb64": "bad", "token": "bad-token"},
                )
                response = self.client.get(url)

                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context["validlink"])    