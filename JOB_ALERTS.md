# External jobs and alerts

This feature stores listings returned by the Jooble REST API, matches them against job seeker alerts, and shows source links in the app. It does not scrape LinkedIn, Naukri, Internshala, or other sites. Configure only a regional API key and endpoint whose terms permit this use and display.

Jooble is an aggregator; its API does not guarantee listings from every named board. A direct connection to LinkedIn, Naukri, or Internshala would require a source-specific authorized feed or partnership.

## Configuration

Add these values to the local `.env` file:

```dotenv
JOOBLE_API_KEY=your-approved-regional-key
JOOBLE_API_URL=https://your-approved-regional-domain/api
```

The URL is the regional API endpoint associated with that key. Jooble documents different keys for different country domains. Do not use a US key for India listings. The example `.env.example` leaves both settings blank intentionally.

The development email backend writes messages to the console. For real email, set your provider's SMTP values in `.env`, including `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and a verified `DEFAULT_FROM_EMAIL`.

## Run the sync

Apply the `jobalerts` database migration, then run:

```powershell
python manage.py migrate
python manage.py sync_external_jobs
```

To sync only one alert, pass `--alert-id <id>`. Schedule the command with the host's scheduler only after checking the provider's request quotas and licensing. Every active alert currently results in a provider search request per run. Jooble's documented free key has a 500-request lifetime limit, so that key is for evaluation rather than recurring production polling.

Schedule daily digests separately:

```powershell
python manage.py send_job_alert_digests
```

Alerts set to “As jobs are found” receive an email when the sync command detects new matches. “Daily digest” alerts accumulate matches until the digest command runs. On-site matches are available on the My job alerts page.

## Data shown

The provider API returns snippets and listing links, not necessarily a complete job description. The app displays the source-provided snippet and links to the provider listing for details and application. It does not generate or infer missing job requirements.
