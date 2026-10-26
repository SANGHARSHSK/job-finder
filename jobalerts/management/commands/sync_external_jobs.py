from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError

from jobalerts.models import JobAlert
from jobalerts.providers import JobProviderError, JoobleProvider
from jobalerts.services import email_matches, sync_alert


class Command(BaseCommand):
    help = "Fetch approved Jooble listings, match them to active alerts, and notify users."

    def add_arguments(self, parser):
        parser.add_argument("--alert-id", type=int, help="Only sync one job alert.")

    def handle(self, *args, **options):
        try:
            provider = JoobleProvider()
        except ImproperlyConfigured as exc:
            raise CommandError(str(exc)) from exc

        alerts = JobAlert.objects.filter(is_active=True).select_related("user")
        if options["alert_id"]:
            alerts = alerts.filter(pk=options["alert_id"])
        if not alerts.exists():
            self.stdout.write("No active job alerts to sync.")
            return

        total_matches = 0
        failures = 0
        for alert in alerts:
            try:
                matches = sync_alert(alert, provider=provider)
                total_matches += len(matches)
                if (
                    alert.frequency == JobAlert.Frequency.IMMEDIATE
                    and alert.email_enabled
                ):
                    pending = list(
                        alert.matches.filter(email_sent_at__isnull=True).select_related("job")
                    )
                    if pending and not email_matches(alert, pending):
                        self.stderr.write(
                            f"Alert {alert.pk}: email not sent; it will be retried on a later sync."
                        )
                self.stdout.write(
                    f"Alert {alert.pk} ({alert.role_title}): {len(matches)} new matches."
                )
            except JobProviderError as exc:
                failures += 1
                self.stderr.write(f"Alert {alert.pk} could not be synced: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete: {total_matches} new matches; {failures} provider errors."
            )
        )
        if failures:
            raise CommandError("Some alerts could not be synced; see errors above.")
