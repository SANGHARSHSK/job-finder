from smtplib import SMTPException

from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .matching import score_job
from .models import ExternalJob, JobAlert, JobAlertMatch
from .providers import JoobleProvider


def _source_datetime(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = parse_datetime(value)
    except ValueError:
        return None
    if parsed and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def _external_job_defaults(item):
    source_url = (item.get("link") or "").strip()
    title = (item.get("title") or "").strip()
    if not title or not source_url.startswith(("https://", "http://")):
        return None
    return {
        "source_name": str(item.get("source") or "").strip()[:160],
        "title": title[:250],
        "company": (item.get("company") or "").strip()[:250],
        "location": (item.get("location") or "").strip()[:250],
        "snippet": str(item.get("snippet") or ""),
        "salary": str(item.get("salary") or "").strip()[:160],
        "employment_type": str(item.get("type") or "").strip()[:100],
        "source_url": source_url[:1000],
        "source_updated_at": _source_datetime(item.get("updated")),
        "is_active": True,
    }


def sync_alert(alert, provider=None):
    """Fetch, persist, deduplicate, and score the provider results for one alert."""
    provider = provider or JoobleProvider()
    new_matches = []
    for item in provider.search(alert):
        if alert.employment_type:
            requested_type = (
                alert.get_employment_type_display().casefold().replace("-", "").replace(" ", "")
            )
            returned_type = (item.get("type") or "").casefold()
            returned_type = returned_type.replace("-", "").replace(" ", "")
            if not returned_type or requested_type not in returned_type:
                continue
        if alert.remote_only:
            listing_text = " ".join(
                str(item.get(field) or "") for field in ("title", "snippet", "location")
            )
            if "remote" not in listing_text.casefold():
                continue
        provider_id = str(item.get("id", "")).strip()
        defaults = _external_job_defaults(item)
        if not provider_id or not defaults:
            continue

        job, _ = ExternalJob.objects.update_or_create(
            provider=provider.provider_id,
            provider_id=provider_id,
            defaults=defaults,
        )
        score, reasons = score_job(alert, item)
        if score < 20:
            continue

        match, created = JobAlertMatch.objects.get_or_create(
            alert=alert,
            job=job,
            defaults={"score": score, "match_reasons": reasons},
        )
        if created:
            new_matches.append(match)
        elif match.score != score or match.match_reasons != reasons:
            match.score = score
            match.match_reasons = reasons
            match.save(update_fields=["score", "match_reasons", "updated_at"])
    return new_matches


def email_matches(alert, matches):
    """Send one concise email for a group of newly matched jobs."""
    matches = list(matches)
    if not matches or not alert.email_enabled or not alert.user.email:
        return False

    lines = [
        f"New jobs matching your {alert.role_title} alert:",
        "",
    ]
    for match in matches:
        job = match.job
        lines.extend(
            [
                job.title,
                f"{job.company or 'Company not listed'} · {job.location or 'Location not listed'}",
                f"Source: {job.source_name or job.provider}",
                f"Apply: {job.source_url}",
                "",
            ]
        )

    try:
        sent = send_mail(
            subject=f"{len(matches)} new job{'s' if len(matches) != 1 else ''} for {alert.role_title}",
            message="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[alert.user.email],
            fail_silently=False,
        )
    except (OSError, SMTPException):
        return False
    if sent:
        JobAlertMatch.objects.filter(pk__in=[match.pk for match in matches]).update(
            email_sent_at=timezone.now()
        )
        return True
    return False


def sync_active_alerts(alerts=None, provider=None):
    alerts = alerts if alerts is not None else JobAlert.objects.filter(is_active=True)
    results = []
    provider = provider or JoobleProvider()
    for alert in alerts.select_related("user"):
        matches = sync_alert(alert, provider=provider)
        if alert.frequency == JobAlert.Frequency.IMMEDIATE:
            email_matches(alert, matches)
        results.append((alert, len(matches)))
    return results


def send_daily_digests():
    sent_count = 0
    alerts = JobAlert.objects.filter(
        is_active=True,
        email_enabled=True,
        frequency=JobAlert.Frequency.DAILY,
    ).select_related("user")
    for alert in alerts:
        pending = list(
            alert.matches.filter(email_sent_at__isnull=True).select_related("job")
        )
        if email_matches(alert, pending):
            sent_count += 1
    return sent_count
