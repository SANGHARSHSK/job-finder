import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class JobProviderError(Exception):
    """A provider request failed or returned an unusable response."""


class JoobleProvider:
    """Small server-side adapter for Jooble's regional REST API."""

    provider_id = "jooble"

    def __init__(self):
        self.api_key = getattr(settings, "JOOBLE_API_KEY", "")
        self.api_url = getattr(settings, "JOOBLE_API_URL", "").rstrip("/")
        if not self.api_key or not self.api_url:
            raise ImproperlyConfigured(
                "Set JOOBLE_API_KEY and JOOBLE_API_URL to an approved regional API endpoint."
            )

    def search(self, alert, page=1, results_per_page=20):
        endpoint = f"{self.api_url}/{self.api_key}"
        from .matching import description_keywords

        keywords = ", ".join(
            part
            for part in (
                alert.role_title,
                alert.skills,
                alert.get_employment_type_display()
                if alert.employment_type
                else "",
                description_keywords(alert.role_description),
            )
            if part
        )
        location = alert.location or "India"
        if alert.remote_only:
            location = f"{location} remote" if alert.location else "remote"

        payload = {
            "keywords": keywords[:500],
            "location": location,
            "page": str(page),
            "ResultOnPage": str(results_per_page),
            "companysearch": False,
        }
        if alert.min_salary:
            payload["salary"] = alert.min_salary
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise JobProviderError(f"Jooble returned HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise JobProviderError("Could not retrieve jobs from Jooble.") from exc

        jobs = payload.get("jobs", []) if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise JobProviderError("Jooble returned an unexpected response.")
        return jobs
