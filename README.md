# Tipout

Tipout is a Django app for restaurant servers to track shift tips, food sales, alcohol sales, assistant-server tip-out, bar tip-out, paycheck totals, and paycheck history.

## Features

- Server signup, login, logout, and password reset.
- Shift logging for tips, food sales, liquor sales, beer sales, wine sales, and assistant percentage.
- Assistant tip-out selector: no assistant, 1%, 2%, or 3%.
- Fixed bar tip-out: 3% of liquor, beer, and wine sales.
- Dashboard with upcoming paycheck estimate.
- Paycheck history with last paid paycheck, last month, all time, week, month, and custom date range views.
- 10% tax paid display for history totals.
- Mobile-first layout with hamburger drawer navigation.
- SendGrid HTTP email backend for password reset email.

## Business Rules

- Combined sales = food sales + liquor sales + beer sales + wine sales.
- Assistant tip-out = food sales * selected assistant percentage.
- Bar tip-out = 3% * (liquor sales + beer sales + wine sales).
- Net tips = tips made - assistant tip-out - bar tip-out.
- Paychecks are biweekly Mondays.
- Anchor paycheck date is August 10, 2026.
- The most recent week is held back for the next paycheck.
- Paycheck history `Last paycheck` means the most recent already-paid paycheck.

## Local Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Apply migrations:

```bash
python manage.py migrate
```

Run the development server:

```bash
python manage.py runserver 127.0.0.1:8000
```

Open:

```text
http://127.0.0.1:8000/
```

## Useful Commands

Run Django checks:

```bash
python manage.py check
```

Run tests:

```bash
python manage.py test
```

Create an admin user:

```bash
python manage.py createsuperuser
```

## Environment Variables

For local development, the app can run with SQLite and default development values.

For production, configure:

```bash
SECRET_KEY=your-production-secret
DEBUG=False
ALLOWED_HOSTS=your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com
```

For SendGrid password reset email:

```bash
SENDGRID_API_KEY=your-sendgrid-api-key
SENDGRID_API_URL=https://api.sendgrid.com/v3/mail/send
DEFAULT_FROM_EMAIL=no-reply@yourdomain.com
SENDGRID_FROM_NAME=Tipout
```

`DEFAULT_FROM_EMAIL` must be a verified sender in SendGrid.

## Railway Deployment Notes

Railway expects the standard dependency file:

```text
requirements.txt
```

This repo also includes `requirement.txt` because it was explicitly requested, but Railway should use `requirements.txt`.

Recommended Railway variables:

```bash
SECRET_KEY=your-production-secret
DEBUG=False
SENDGRID_API_KEY=your-sendgrid-api-key
SENDGRID_API_URL=https://api.sendgrid.com/v3/mail/send
DEFAULT_FROM_EMAIL=no-reply@yourdomain.com
SENDGRID_FROM_NAME=Tipout
```

If using Railway Postgres, connect these variables from the Postgres service:

```bash
PGDATABASE=${{Postgres.PGDATABASE}}
PGUSER=${{Postgres.PGUSER}}
PGPASSWORD=${{Postgres.PGPASSWORD}}
PGHOST=${{Postgres.PGHOST}}
PGPORT=${{Postgres.PGPORT}}
```

Recommended production start command:

```bash
gunicorn settings.wsgi
```

Before deploying to Railway, update `settings/settings.py` to read production database, allowed hosts, and CSRF from environment variables.

## Static Files

The app uses WhiteNoise for production static files. Railway should run:

```bash
python manage.py collectstatic --noinput
```

before the app starts. Static output is collected into `staticfiles/`, which is intentionally ignored by git.

## Dependency Files

- `requirements.txt`: standard file for deployment platforms.
- `requirement.txt`: duplicate dependency file requested for this project.
