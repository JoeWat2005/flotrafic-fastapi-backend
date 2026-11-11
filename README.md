# Flotrafic API (FastAPI)

FastAPI backend for Flotrafic, providing business accounts, public business websites, enquiries, bookings, Stripe subscriptions and transactional email.

Status: beta, last updated February 2026. This is a rebuild of the original [Flask backend](https://github.com/JoeWat2005/flotrafic-flask-backend). Flotrafic is an earlier product that preceded [DeskCaptain](https://github.com/JoeWat2005/deskcaptain).

## Features

- Business sign-up with emailed six-digit verification codes, Cloudflare Turnstile checks and Argon2 password hashing
- JWT bearer authentication (HS256, 24-hour tokens) and password reset by emailed code
- Business-scoped APIs for the account (`/me`), enquiries, bookings and website customisation, including logo uploads
- Public, unauthenticated endpoints behind each business's website: business data, enquiries, booking requests and visit tracking
- Free and Pro tiers, with Stripe Checkout for Pro and a Stripe webhook that keeps subscription state in sync
- Admin login and admin-only routes to list, re-tier, suspend, activate and delete businesses
- Audit log of key actions, in-memory rate limiting on public and auth routes, and a 60-second in-memory cache for public business data
- Transactional emails sent through Brevo templates for verification, password reset, enquiries, bookings and subscription changes

## Tech stack

- Python 3.11 (the Docker base image is `python:3.11-slim`)
- FastAPI 0.128 and Pydantic 2
- SQLAlchemy 2.0
- python-jose for JWTs, and passlib with argon2-cffi for password hashing
- Stripe Python SDK 14
- Brevo transactional email SDK (`sib_api_v3_sdk`)
- Gunicorn with Uvicorn workers

## Getting started

### Prerequisites

- Python 3.11
- A Stripe account with a recurring price for the Pro plan and a webhook signing secret
- A Brevo account with the transactional templates the code refers to (template IDs 10 to 21 in `app/services/email.py`)
- A Cloudflare Turnstile secret key

### Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install pydantic-settings sib-api-v3-sdk
```

The last line is needed because `requirements.txt` leaves out two packages the code imports: `pydantic-settings` (used in `app/core/config.py`) and the Brevo SDK `sib_api_v3_sdk` (used in `app/core/utils.py`).

### Configuration

Settings are read from environment variables or from a `.env` file in the working directory (`app/core/config.py`). `.env` is ignored by git.

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Yes | SQLAlchemy database URL. See the note below. |
| `JWT_SECRET_KEY` | Yes | Secret used to sign access tokens |
| `STRIPE_SECRET_KEY` | Yes | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Yes | Signing secret for `POST /stripe/webhook` |
| `STRIPE_PRO_PRICE_ID` | Yes | Stripe price used for Pro checkout |
| `TURNSTILE_SECRET_KEY` | Yes | Cloudflare Turnstile secret used to verify captcha tokens |
| `ADMIN_PASSWORD` | Yes | Saved as the seeded admin account's password hash. See the note below. |
| `BREVO_API_KEY` | Yes | Brevo API key. Optional in the settings class, but `app/core/utils.py` raises an error at import if it is missing. |
| `FRONTEND_URL` | No | Frontend base URL used for Stripe redirect URLs (default `http://localhost:5173`) |

Notes:

- `app/db/session.py` passes `check_same_thread=False` to the engine. Only SQLite accepts that option, so as written the app needs a SQLite `DATABASE_URL`, even though `psycopg2-binary` is installed.
- On startup the app creates an admin account (`app/db/seed.py`) and copies `ADMIN_PASSWORD` straight into its `hashed_password` field. Admin login checks passwords with Argon2, so `ADMIN_PASSWORD` must be an Argon2 hash rather than a plain password.

### Running locally

```bash
mkdir uploads
uvicorn app.main:app --reload --port 8000
```

`app/main.py` serves the `uploads` folder at `/media` for logo files and fails at startup if that folder does not exist. On startup the app also creates any missing tables (`Base.metadata.create_all`) and seeds the admin account. FastAPI's interactive API docs are available at `/docs`.

Port 8000 matches what the [React frontend](https://github.com/JoeWat2005/flotrafic-react-frontend) expects, and CORS already allows `http://localhost:5173`. To test billing, Stripe must be able to reach `POST /stripe/webhook`.

### Docker

```bash
docker build -t flotrafic-api .
docker run -p 8000:8000 --env-file .env flotrafic-api
```

The image runs Gunicorn with four Uvicorn workers bound to `0.0.0.0:8000`. There is no `.dockerignore`, so `COPY . .` also copies any local `.env` and `uploads/` into the image. The `uploads` folder still has to exist in the build context for the container to start.

### Tests

`app/api/tests/` holds empty placeholder files only, so there are no tests to run yet.

## How it works

`app/main.py` creates the app, mounts `/media`, configures CORS for local development and the production frontend domains, creates the tables, seeds the admin and includes the router from `app/api/router.py`.

### Routes

All route modules live in `app/api/routes/`.

| Prefix | Module | Access | Purpose |
| --- | --- | --- | --- |
| `/auth` | `auth.py` | Public | Login, pre-registration, email verification, Stripe checkout start, password reset |
| `/admin/auth` | `admin_auth.py` | Public | Admin login |
| `/me` | `me.py` | Business | Account details and billing summary |
| `/enquiries` | `enquiries.py` | Business, tier feature | List, mark as read, change status, delete, stats |
| `/bookings` | `bookings.py` | Business, tier feature | List, confirm, delete, create from an enquiry, edit notes |
| `/customisation` | `customisation.py` | Business, tier feature | Website settings and logo upload |
| `/billing` | `billing.py` | Business | Billing overview. Checkout, portal, cancel and resume currently return 503 while Pro is disabled. |
| `/public` | `public.py` | Public, rate limited | Business site data, enquiries, booking requests, visit tracking |
| `/stripe` | `stripe_webhook.py` | Stripe signature | Subscription and invoice webhooks |
| `/businesses` | `business.py` | Admin | List, change tier, suspend, activate, delete businesses |

### Authentication and access

`app/core/security.py` hashes passwords, issues tokens, verifies Turnstile tokens and applies rate limits. `app/api/deps.py` decodes bearer tokens. Business tokens must belong to a verified, active business, and admin tokens carry `type: admin`. `require_feature()` checks the business's tier against the `TIERS` table in `app/core/config.py`.

### Billing

`POST /auth/start-checkout` creates a Stripe Checkout subscription session for the Pro price. `POST /stripe/webhook` verifies the Stripe signature and records each event ID in `stripe_events` so duplicates are skipped. It handles these events:

- `checkout.session.completed`
- `customer.subscription.created`, `customer.subscription.updated` and `customer.subscription.deleted`
- `invoice.paid`, `invoice.payment_succeeded` and `invoice.payment_failed`

`apply_subscription_state()` in `app/core/config.py` derives the tier from the latest paid invoice period or the subscription status.

### Data, email and caching

- **Data.** `app/db/models.py` defines businesses, enquiries, bookings, contact messages, admins, audit logs, visits, business customisations, business availability and processed Stripe events. Tables are created at startup, and there are no migrations.
- **Email.** `app/services/email.py` wraps the Brevo transactional templates. Public enquiries notify the business, and booking requests notify both the business and the customer. Confirmations and cancellations email the customer, and Stripe events trigger subscription emails.
- **Rate limits and cache.** The rate limiter and the public business cache are in-process dictionaries. They reset on restart and are not shared between Gunicorn workers.

## Known issues

- `requirements.txt` is missing `pydantic-settings` and the Brevo SDK (see Installation). It is also saved as UTF-16, which pip can read but some other tools cannot.
- The `Business` model has no `stripe_subscription_status` column, but `GET /me/billing` and the Pro-tier check in `require_feature()` read that attribute and will raise an error. The Stripe sync code sets it without saving it.
- `auth.py` and `stripe_webhook.py` print debug output to stdout, including generated verification codes.
- `app/api/routes/settings.py` and `app/core/redis.py` are placeholders.

## Project structure

```
app/
  api/
    routes/      Route modules (auth, enquiries, bookings, public, billing, webhooks, admin)
    tests/       Empty placeholder test files
    deps.py      Authentication and feature-gating dependencies
    router.py    Combines all route modules
  core/          Settings, security helpers, Stripe and Brevo utilities
  db/            SQLAlchemy models, session and admin seeding
  schemas/       Pydantic request and response models
  services/      Audit logging and email senders
  main.py        Application entry point
Dockerfile       Production image (Gunicorn with Uvicorn workers)
requirements.txt Python dependencies
```

## Related repositories

- [flotrafic-react-frontend](https://github.com/JoeWat2005/flotrafic-react-frontend): the React frontend that uses this API
- [flotrafic-flask-backend](https://github.com/JoeWat2005/flotrafic-flask-backend): the original Flask backend that this replaces
- [deskcaptain](https://github.com/JoeWat2005/deskcaptain): the later AI receptionist product
