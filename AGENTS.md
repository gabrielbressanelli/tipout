# Tipout Project Context

## Product

Tipout is a simple Django app for restaurant servers. Servers log in, enter shift tips and sales, choose an assistant-server percentage, and see their expected paycheck total.

## Current Stack

- Python with Django 6.0.3.
- SQLite database at `db.sqlite3` for local development; production uses Postgres when Railway `PG...` variables exist.
- Main Django app: `tips`.
- Settings package: `settings`.

## Current Features

- Server signup, login, and logout.
- Password reset flow using Django auth views and a custom SendGrid HTTP email backend.
- Authenticated dashboard at `/`.
- Shift entry form with:
  - service date
  - tips made
  - food sales
  - liquor sales
  - beer sales
  - wine sales
  - assistant server percent: 0%, 1%, 2%, or 3%
- Recent shift log with delete action.
- Mobile-first templates and CSS.
- Mobile authenticated navigation uses a hamburger button with a left-side drawer.
- Brand assets live in `tips/static/tips/brand/`; header/auth pages use `logo.png`, and favicon links use the generated favicon package.
- Glass-style toast notifications for saved/deleted shifts, auto-dismissed after 4 seconds.
- Paycheck history page at `/paychecks/` with last paid paycheck, last month, all-time, week, month, and custom range views.
- Production static files are served with WhiteNoise. `collectstatic` is preferred, but `WHITENOISE_USE_FINDERS=True` is enabled by default so app static files can still serve if Railway skips static collection.

## Business Rules

- Combined sales = food sales + liquor sales + beer sales + wine sales.
- Assistant tip-out = food sales * selected assistant percentage.
- Bar tip-out = 3% * (liquor sales + beer sales + wine sales), regardless of assistant selection.
- Net tips = tips made - assistant tip-out - bar tip-out.
- Paycheck history shows `Total` before tax and a separate `10% tax paid` amount. Do not add an after-tax total unless explicitly requested.
- In paycheck history, `Last paycheck` means the most recent already-paid paycheck, not the upcoming paycheck.
- Paychecks are biweekly Mondays.
- Anchor paycheck date is August 10, 2026.
- The August 10, 2026 paycheck pays July 20, 2026 through August 2, 2026.
- The most recent week is always held back for the next paycheck.

## Important Files

- `tips/models.py`: profile, tip entry model, money helpers, paycheck-window logic.
- `tips/forms.py`: signup and tip-entry forms.
- `tips/views.py`: dashboard, signup, delete-entry views.
- `tips/views.py`: also contains paycheck-history date range and reporting helpers.
- `settings/urls.py`: app, auth, and admin routes.
- `tips/templates/`: base, auth, and dashboard templates.
- `tips/email_backends.py`: SendGrid Mail Send API backend using environment variables.
- `tips/static/tips/styles.css`: responsive styling.
- `tips/static/tips/toasts.js`: timed toast notification behavior.
- `tips/static/tips/nav.js`: mobile drawer navigation behavior.
- `tips/tests.py`: calculation and paycheck-window tests.
- `README.md`: project setup, commands, environment variables, and Railway notes.
- `requirements.txt`: standard dependency file generated from `.venv`.
- `requirement.txt`: duplicate dependency file requested by the user.
- `nixpacks.toml`: Railway build/start config; runs `collectstatic`, `migrate`, then Gunicorn.

## Local Commands

- Run checks: `python3 manage.py check`
- Run tests: `python3 manage.py test`
- Apply migrations: `python3 manage.py migrate`
- Start dev server: `python3 manage.py runserver 127.0.0.1:8000`
- SendGrid variables: `SENDGRID_API_KEY`, `SENDGRID_API_URL`, `DEFAULT_FROM_EMAIL`, `SENDGRID_FROM_NAME`.

## Verification From Initial Build

- `python3 manage.py check` passed.
- `python3 manage.py test` passed.
- `/login/`, `/signup/`, and `/` rendered successfully through Django's test client.
- The local dev server responded at `/login/` after running outside the sandbox.

## Session Memory Rules

- Keep this file updated when project goals, business rules, setup commands, or architectural decisions change.
- Keep durable rules here instead of relying only on chat memory.
- Do not store secrets, passwords, API keys, or personal employee data in this file.
