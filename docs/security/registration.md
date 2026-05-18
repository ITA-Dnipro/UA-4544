# Registration Security Runbook

## Overview

The registration endpoint (`POST /api/auth/register/`) is protected by:
1. **reCAPTCHA v2** — bot mitigation via Google's "I'm not a robot" checkbox
2. **Rate limiting** — per-IP throttle via Django REST Framework
3. **CORS policy** — only allowed frontend origins can make requests

---

## 1. Bot Protection — reCAPTCHA v2

**How it works:**
- Frontend renders a Google reCAPTCHA v2 widget (checkbox "I'm not a robot")
- On submit, the frontend includes a `recaptcha_token` in the POST body
- Backend verifies the token against Google's `siteverify` API using `RECAPTCHA_SECRET_KEY`
- If verification fails → `400 Bad Request` with `{"detail": "Invalid captcha. Please try again."}`
- If `RECAPTCHA_SECRET_KEY` is empty (local dev without key) → verification is skipped

**Frontend component:** `react-google-recaptcha`
**Site key env var:** `VITE_RECAPTCHA_SITE_KEY` (frontend `.env`)
**Secret key env var:** `RECAPTCHA_SECRET_KEY` (backend `.env`)

> ⚠️ For local development, use Google's public test keys (always pass).
> For production, register real keys at https://www.google.com/recaptcha/admin

---

## 2. Rate Limiting

### 2a. Per-IP throttling (DRF ScopedRateThrottle)

Configured in `settings.py` via `DEFAULT_THROTTLE_RATES`:

| Endpoint | Scope | Limit |
|---|---|---|
| `POST /api/auth/register/` | `register` | 5 requests / hour per IP |
| `POST /api/auth/login/` | `login` | 10 requests / hour per IP |
| `POST /api/auth/password-reset/` | `password_reset` | 5 requests / hour per IP |

Throttle class: `ScopedRateThrottle` (DRF built-in)
Cache backend: Django default cache (LocMemCache in dev)

When limit is exceeded → `429 Too Many Requests`

### 2b. Per-email throttling (registration)

Implemented via `users/security.py`:

| Endpoint | Limit | Lockout |
|---|---|---|
| `POST /api/auth/register/` | 5 attempts / hour per email | 1 hour |

- Counted: `record_register_attempt(email)` — only on failed registration attempts (serializer validation error)
- Checked: `is_register_locked(email)` — at the very start of the request
- Active only when `RECAPTCHA_SECRET_KEY` is set (production)
- Uses cache keys `auth:register:count:{email}` and `auth:register:lock:{email}`
- Separate from login per-email protection (`auth:login:*` keys)

## 3. CORS Policy

Only the configured frontend origin(s) are allowed to make API requests from the browser.

**Config:** `CORS_ALLOWED_ORIGINS` in `settings.py` (read from `.env`)
**Default (dev):** `http://localhost:5173, http://127.0.0.1:5173, http://frontend:5173`
**Production:** set `CORS_ALLOWED_ORIGINS` in CI/CD secrets or server environment

> ℹ️ CORS only restricts browser-based requests. Server-to-server calls are not blocked by CORS.
> Rate limiting and reCAPTCHA cover non-browser attack vectors.

---

## 4. Required Environment Variables

### Backend (`scalea/.env`)

| Variable | Description | Where to get |
|---|---|---|
| `RECAPTCHA_SECRET_KEY` | reCAPTCHA v2 secret key for server-side verification | https://www.google.com/recaptcha/admin |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins | Set per environment |

### Frontend (`frontend/.env`)

| Variable | Description | Where to get |
|---|---|---|
| `VITE_RECAPTCHA_SITE_KEY` | reCAPTCHA v2 public site key for widget rendering | https://www.google.com/recaptcha/admin |

> For local development, use Google's public test keys (see `.env.example` files).

---

## 5. Monitoring & Alerting

### Unusual Signup Spikes
**Trigger:** More than 50 registration attempts within 5 minutes from various IPs

**Actions:**
1. Check server logs: `grep "POST /api/auth/register/" access.log | tail -100`
2. Identify suspicious IPs and block at nginx/firewall level
3. Temporarily tighten rate limit: change `'register': '5/hour'` to `'register': '2/hour'`
4. Notify DevOps if attack is ongoing

### High Email Bounce Rate
**Trigger:** Email bounce rate > 10% (emails rejected by recipients' mail servers)

**What it means:** Bots are registering with fake/non-existent emails, causing your email provider to flag your account as spam.

**Actions:**
1. Check bounce reports in your email provider dashboard (Gmail, SendGrid, etc.)
2. If rate > 10%: tighten reCAPTCHA (switch to invisible reCAPTCHA or add email domain validation)
3. If rate > 30%: contact email provider support to avoid account suspension
4. Consider adding email existence verification (MX record check) before sending

### Resend Verification Abuse
**Trigger:** Same email requesting resend > 3 times / hour

**Actions:** Rate limit on `/api/auth/resend-verification/` is handled in task #99 (i-taras).
