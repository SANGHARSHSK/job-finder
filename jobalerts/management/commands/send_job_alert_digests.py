from django.core.management.base import BaseCommand

from jobalerts.services import send_daily_digests


class Command(BaseCommand):
    help = "Email pending matches for active daily job alerts."

    def handle(self, *args, **options):
        sent = send_daily_digests()
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} daily job alert digests."))
