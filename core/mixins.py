from django.contrib.auth.mixins import UserPassesTestMixin

from accounts.models import User


class RoleRequiredMixin(UserPassesTestMixin):
    """Restrict a view to authenticated users with one specific role.

    Anonymous users are redirected to the login page. Logged-in users with
    the wrong role receive a 403 Forbidden response.
    """

    required_role = None

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.role == self.required_role


class JobSeekerRequiredMixin(RoleRequiredMixin):
    required_role = User.Role.JOB_SEEKER


class EmployerRequiredMixin(RoleRequiredMixin):
    required_role = User.Role.EMPLOYER