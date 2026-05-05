# UA-4544
![CI Status](https://github.com/ITA-Dnipro/UA-4544/actions/workflows/ci.yml/badge.svg)
![Codecov](https://codecov.io/gh/ITA-Dnipro/UA-4544/branch/develop/graph/badge.svg)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![Dependabot](https://img.shields.io/badge/dependabot-enabled-brightgreen.svg)

UA-4544 Project-based learning Full Stack Python/React

**Project Vision Statement:**

_"Empowering Innovation: Bridging Startups and Investors for Ukraine's Economic Growth"_

**Overview:**

In the dynamic world of entrepreneurship, the path from a transformative idea to a successful venture is often complex and challenging. Our WebAPI application, developed using the Django Rest Framework, is designed to be a cornerstone in simplifying this journey. We aim to create a robust and secure digital platform that caters to two pivotal groups in the business ecosystem: innovative startups with compelling ideas and forward-thinking investors seeking valuable opportunities.

**Goals:**

1. **Fostering Collaborative Opportunities:** Our platform bridges startups and investors, enabling startups to showcase their groundbreaking proposals and investors to discover and engage with high-potential ventures.

2. **Seamless User Experience:** We prioritize intuitive navigation and interaction, ensuring that startups and investors can easily connect, communicate, and collaborate.

3. **Secure and Trustworthy Environment:** Security is at the forefront of our development, ensuring the confidentiality and integrity of all shared information and communications.

4. **Supporting Economic Growth:** By aligning startups with the right investors, our platform not only cultivates individual business success but also contributes significantly to the growth and diversification of Ukraine's economy.

**Commitment:**

We are committed to delivering a platform that is not just a marketplace for ideas and investments but a thriving community that nurtures innovation fosters economic development, and supports the aspirations of entrepreneurs and investors alike. Our vision is to see a world where every transformative idea has the opportunity to flourish and where investors can confidently fuel the engines of progress and innovation.

![image](https://github.com/mehalyna/Forum-Project-Stage-CC/assets/39273210/54b0de76-f6e3-4bf3-bf38-fb5bf1d1d63d)

## Registration anti-enumeration policy

The registration endpoint (`POST /api/auth/register/`) always returns `201` with a generic success message.
If the email already exists and the user is already verified, the backend performs no side effects.
If the email exists but is not yet verified, the backend may re-send the verification email.

### Login Endpoint

The login endpoint (`POST /api/auth/login/`) authenticates a user using email, password, and selected role, and returns JWT access and refresh tokens.

#### Endpoint

**POST** `/api/auth/login/`

#### Request Body

```json
{
  "email": "user@example.com",
  "password": "P@ssw0rd",
  "role": "startup",
  "remember": true
}
```

#### Request Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `email` | string | yes | User email address |
| `password` | string | yes | User password |
| `role` | string | yes | Selected login role: `startup` or `investor` |
| `remember` | boolean | no | If `true`, extends refresh token lifetime to 30 days and access token lifetime to 12 hours |

#### Success Response: `200 OK`

```json
{
  "access": "<jwt-access-token>",
  "refresh": "<jwt-refresh-token>",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "role": "startup"
  }
}
```

#### Response Fields

| Field | Type | Description |
|---|---|---|
| `access` | string | JWT access token |
| `refresh` | string | JWT refresh token |
| `user.id` | integer | User ID |
| `user.email` | string | User email |
| `user.role` | string | Authenticated role selected during login |

#### Error Responses

**`400 Bad Request`** — invalid or missing fields

```json
{
  "role": ["This field is required."]
}
```

**`401 Unauthorized`** — invalid credentials or role mismatch

```json
{
  "detail": ["Invalid email or password."]
}
```

**`429 Too Many Requests`** — temporary lockout after repeated failed attempts

```json
{
  "detail": ["Too many failed attempts. Try again later."]
}
```

#### Security Features

✅ **Generic authentication failure**
- Returns the same `401` message for:
  - invalid email
  - wrong password
  - wrong role
- Prevents account enumeration and role discovery

✅ **Role-aware authentication**
- Users must choose a role (`startup` or `investor`) during login
- Login succeeds only if the authenticated user has the selected role
- Users with both roles may log in as either role

✅ **Brute-force protection**
- Failed attempts are tracked per email
- After repeated failures, login is temporarily locked

✅ **Throttle protection**
- Login endpoint is protected with DRF scoped throttling

#### Token Lifetime Policy

- Default access token lifetime is controlled by `SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']`
- Default refresh token lifetime is controlled by `SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']`
- If `remember=true`:
  - refresh token lifetime is extended to **30 days**
  - access token lifetime is extended to **12 hours**

### Refresh & Logout

The backend supports:

- `POST /api/auth/refresh/`
- `POST /api/auth/logout/`

Auth session management includes token refresh and refresh-token revocation on logout.
After successful password reset confirmation, all active refresh tokens for the user are revoked (existing sessions are invalidated).

Detailed request/response examples and security/session policies (TTL, throttling, token revocation, and password-reset session invalidation) are documented in the project wiki.

### Password Reset Flow

The password reset endpoint (`POST /api/auth/password-reset/`) implements a secure password reset mechanism with anti-enumeration protection.

#### Endpoint

**POST** `/api/auth/password-reset/`

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:** Always `200 OK`
```json
{
  "detail": "If the email exists, you will receive reset instructions."
}
```

#### Security Features

✅ **Anti-Enumeration Protection**
- Always returns `200 OK` regardless of whether email exists
- Same response message for existing and non-existing emails
- Prevents attackers from discovering valid email addresses

✅ **Rate Limiting**
- **IP-based:** 5 requests per hour per IP address
- **Email-based:** 3 requests per hour per email address
- Returns `429 Too Many Requests` when limits exceeded

✅ **Token Security**
- Cryptographically secure tokens using Django's `PasswordResetTokenGenerator`
- Tokens expire after 1 hour (configurable via `PASSWORD_RESET_TIMEOUT`)
- One-time use tokens
- Only active, verified users receive reset emails

✅ **Audit Logging**
- All password reset attempts logged to `PasswordResetAttempt` model
- Tracks: user, email, IP address, token sent status, timestamp
- Enables security monitoring and abuse detection

#### Email Template

When a valid user requests a password reset, they receive an email containing:

**Subject:** `Password Reset Request - Startup Gateway`

**Reset Link Format:**
```
{protocol}://{domain}/reset-password?uid={uid}&token={token}

Example:
https://startup-gateway.com/reset-password?uid=MQ&token=c7g8h9-abc123def456
```

**Link Parameters:**
- `uid` - Base64-encoded user ID
- `token` - Secure, time-limited reset token (valid for 1 hour)

**Email Templates Location:**
- Plain text: `templates/emails/password_reset.txt`
- HTML: `templates/emails/password_reset.html`

#### Configuration

**Settings (settings.py):**
```python
# Password reset token expiry (in seconds)
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour

# Email configuration
DEFAULT_FROM_EMAIL = 'no-reply@startup-gateway.com'
SITE_NAME = 'Startup Gateway'
FRONTEND_URL = 'http://localhost:5173'

# Throttling
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'password_reset': '5/hour',
    }
}
```

#### Testing

Run password reset tests:
```bash
python manage.py test users.tests.TestPasswordResetApi -v 2
```

**Test Coverage:**
- Email sent for known, active users
- No email for unknown users
- No email for inactive users
- Email normalization (lowercase)
- Rate limiting (IP and email)
- Audit logging with IP tracking
- Token generation and validation
- Anti-enumeration verification
- Email content validation

#### API Usage Example
```bash
# Request password reset
curl -X POST http://localhost:8000/api/auth/password-reset/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'

# Response
{
  "detail": "If the email exists, you will receive reset instructions."
}
```

#### Database Schema

**PasswordResetAttempt Model:**
```python
class PasswordResetAttempt(models.Model):
    user = models.ForeignKey(User, null=True, blank=True)
    email = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField()
    token_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
```

#### Implementation Notes

The password reset flow consists of two steps:

1. **Request** (implemented) - User requests reset via email, receives link
2. **Confirm** (to be implemented) - User submits new password with uid/token from email

This endpoint implements step 1. The confirm endpoint will validate the uid/token and allow the user to set a new password.

---

### Basic Epics

0. **As a user of the platform**, I want the ability to represent both as a startup and as an investor company, so that I can engage in the platform's ecosystem from both perspectives using a single account.
   - Features:
     - implement the functionality for users to select and switch roles.

1. **As a startup company,** I want to create a profile on the platform, so that I can present my ideas and proposals to potential investors.
   - Features:
     - user registration functionality for startups.
     - profile setup page where startups can add details about their company and ideas.

2. **As an investor,** I want to view profiles of startups, so that I can find promising ideas to invest in.
   - Features:
     - feature for investors to browse and filter startup profiles.
     - viewing functionality for detailed startup profiles.

3. **As a startup company,** I want to update my project information, so that I can keep potential investors informed about our progress and milestones.
   - Features:
     - functionality for startups to edit and update their project information.
     - system to notify investors about updates to startups they are following.

4. **As an investor,** I want to be able to contact startups directly through the platform, so that I can discuss investment opportunities.
   - Features:
     - secure messaging system within the platform for communication between startups and investors.
     - privacy and security measures to protect the communication.

5. **As a startup company,** I want to receive notifications about interested investors, so that I can engage with them promptly.
   - Features:
     - notification functionality for startups when an investor shows interest or contacts them.
     - dashboard for startups to view and manage investor interactions.

6. **As an investor,** I want to save and track startups that interest me, so that I can manage my investment opportunities effectively.
   - Features:
     - feature for investors to save and track startups.
     - dashboard for investors to manage their saved startups and investment activities.

### Additional Features

- **Security and Data Protection**: Ensure that user data, especially sensitive financial information, is securely handled.

- **User Feedback System**: Create a system for users to provide feedback on the platform, contributing to continuous improvement.
- **Analytical Tools**: Implement analytical tools for startups to understand investor engagement and for investors to analyze startup potential.

### Agile Considerations

- Each user story can be broken down into smaller tasks and developed in sprints.
- Regular feedback from both user groups (startups and investors) should be incorporated.

### Database Schema

![Database Schema](docs/images/DB_schema.jpg)

## Automation & Quality

### CI Pipeline

This project uses **GitHub Actions** for continuous integration.

#### Jobs

| Job | What it runs |
|-----|-------------|
| `lint-and-test` | Ruff lint, Ruff format, Codecov |
| `frontend-build` | ESLint, TypeScript check, Vite production build |

#### Triggers

- Push to `main` or `develop`
- Pull requests to `main` or `develop`

#### Running CI checks locally

**Backend:**
```bash
ruff check scalea/
ruff format --check scalea/
pytest --cov=scalea
```

**Frontend:**
```bash
cd frontend
npm install
npm run lint
npm run build
```

### Code Coverage
Project uses **Codecov** to monitor test coverage and ensure code reliability.

* **Automation:** Coverage is uploaded automatically as part of the CI pipeline
* **Setup:** CI includes a Codecov upload step.

To enable coverage upload:
1. Add `CODECOV_TOKEN` to **Settings > Secrets and variables > Actions**.
2. Run the CI pipeline

### Dependabot
**Dependabot** is enabled to keep dependencies up to date and secure. It monitors:
* **GitHub Actions** (CI/CD workflows)
* **Python** (pip)
* **Frontend** (npm packages)

#### Step 1: Installation

**Action**: All dependencies can be installed with a single pip command ran from the project root.

**Command:**

```bash
pip install -e .
```

For developers, there is an additional layer of dependencies to install.

**Command:**

```bash
pip install -e ".[dev]"
```

#### Step 2: Running the linter
Install packages from the `dev` extras to get access to the linter and formatter.

This project uses:
- **Ruff** for Python linting/formatting (backend)
- **ESLint** for TypeScript/React linting (frontend)

##### Backend (Python) — Ruff
(From project root)

To lint and format your staged files, run the following command from the project root:
```bash
ruff check .
ruff check . --fix
ruff format .
```

##### Frontend (React) — ESLint
(From `frontend` directory)

To lint and format your staged files, run the following command:
```bash
npm install
npm run lint
npm run lint:fix
```

##### Install & Run pre-commit
**Command:**
```bash
pre-commit install
```

```bash
pre-commit run
```

Alternatively, if you want to lint and format all files, run:

**Command:**

```bash
pre-commit run --all-files
```

Run specific hooks:
**Command:**
```bash
pre-commit run ruff-check --all-files
pre-commit run ruff-format --all-files
pre-commit run frontend-eslint --all-files
```

#### GitHub Actions

Ruff checks are run locally via pre-commit and should also be enforced in CI

**Local Development with Docker**

This project provides a containerized environment for consistent development across machines using Docker.

---

## Prerequisites

- [Docker](https://www.docker.com/get-started) installed and running
- [Docker Compose](https://docs.docker.com/compose/install/) installed

## Environment Variables

1. **Copy the root `.env` example:**

```bash
cp env.example .env
```

2. **Copy the backend Docker env example:**

```bash
cp scalea/.env.example scalea/.env.docker
```

3. **Copy the frontend Docker env example:**

```bash
cp frontend/.env.example frontend/.env
```


4. **Edit all files and fill in real values.**  
   `.env` and `scalea/.env.docker` and `frontend/.env` must **not** be committed to Git — they are included in `.gitignore`.
---

## Running the Project

### Step 1 — Build and start all services

```bash
docker-compose up --build
```

This will build images and start the following services:

| Service    | Description                        | Port  |
|------------|------------------------------------|-------|
| `db`       | PostgreSQL 15                      | 5432  |
| `redis`    | Redis 7 (channels / notifications) | 6379  |
| `mongo`    | MongoDB 7.0                        | 27017 |
| `backend`  | Django REST Framework (dev)        | 8000  |
| `frontend` | React + Vite (dev mode)            | 5173  |


## Stopping the Containers

Stop all running containers (preserves volumes):

```bash
docker-compose down
```

Stop all running containers (remove volumes):

```bash
docker-compose down -v
```
