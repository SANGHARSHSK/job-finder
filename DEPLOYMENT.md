# Production deployment

This Django app is configured for a Linux WSGI host with PostgreSQL, HTTPS, WhiteNoise static files, and a health endpoint at `/health/`. Deploy to a staging environment first.

## Temporary interview demo on Render

The repository includes `render.yaml` for a temporary Render deployment. Connect the GitHub repository to Render and create a Blueprint from that file. Render creates the web service and PostgreSQL database, generates the Django secret, runs migrations, seeds six clearly labeled fictional jobs, and publishes an `onrender.com` URL.

This Blueprint uses Render's free plans for an interview demo only. The web process sleeps after 15 minutes without traffic and may take about a minute to wake. The free database expires after 30 days. The service filesystem is temporary, so uploaded resumes are not durable. Do not ask interviewers or other visitors to upload real resumes, and do not use this setup for real applicants. Open the site shortly before the interview to wake it up.

For durable use, change to paid resources and configure persistent private resume storage, backups, and an email provider before accepting real users.

## Required production configuration

Set these as platform environment variables; do not commit a production `.env` file:

- `DEBUG=False`
- `SECRET_KEY`: generate a new, unique secret with Django's `get_random_secret_key()` and store it in the platform secret manager.
- `ALLOWED_HOSTS`: comma-separated hostnames, without schemes (for example, `jobs.example.com`).
- `CSRF_TRUSTED_ORIGINS`: full origins including `https://` when the host uses a separate origin.
- `DATABASE_URL`: a managed PostgreSQL URL. Require TLS using the provider's documented connection options.
- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` plus the provider SMTP host, port, TLS mode, username, password, and verified `DEFAULT_FROM_EMAIL`.
- `MEDIA_ROOT`: durable private storage for uploaded resumes. The default filesystem storage is not durable on ephemeral hosts. Attach persistent storage or configure private object storage before accepting applications; never expose the resume directory as public static files.

`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, and `CSRF_COOKIE_SECURE` default to enabled when `DEBUG=False`. The app trusts `X-Forwarded-Proto` from its deployment proxy; deploy only behind a proxy that overwrites that header. HSTS defaults to one year in production. Set `SECURE_HSTS_SECONDS=0` until HTTPS is working for the production domain; enable it only after TLS is confirmed.

## Build and release

Use these commands in the platform configuration:

```sh
pip install -r requirements.txt
python manage.py collectstatic --noinput
```

Run database migrations as a release step before routing traffic:

```sh
python manage.py migrate
```

Start the web process with:

```sh
gunicorn jobfinder.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --access-logfile -
```

Configure the platform health check to request `/health/`. It returns `200` only when Django can reach PostgreSQL.

## Before opening registration

- The Render interview Blueprint seeds six clearly marked fictional job listings. Remove them before using the deployment for real hiring. The development database also contains fictional sample listings.
- Confirm uploaded resumes persist across deploys and are accessible only through the authenticated resume download view.
- Verify SMTP delivery, password reset, registration, employer posting, applicant status updates, and alert email delivery in staging.
- Configure database backups, log retention, domain TLS, and a process restart policy on the hosting platform.
- Review `python manage.py check --deploy` output with the actual production environment.

Jobs must be reconfirmed by their employer every 30 days to stay visible and accept applications. Editing an open job or using “Confirm still open” refreshes its confirmation date. This is a freshness signal, not an identity or legitimacy guarantee.
