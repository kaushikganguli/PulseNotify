# PulseNotify

Django REST Framework backend for flight-price alerts with JWT, PostgreSQL, Redis, Celery and Celery Beat.

## Contents
- Register/login with JWT access tokens
- UserProfile auto-created via `post_save`; registration always assigns `user`
- Create/list/deactivate alerts, scoped to the authenticated user
- Public mock flight price feed for four routes
- Admin-role-only summary endpoint
- Celery price checker scheduled every 60 seconds and asynchronous notification task
- PostgreSQL + Redis in Docker Compose, split settings, tests and Postman collection

## Setup
Requirements: Python 3.11+, Docker, Docker Compose.

1. Copy `.env.example` to `.env` and change `SECRET_KEY` and passwords.
   - Windows PowerShell: `Copy-Item .env.example .env`
   - macOS/Linux: `cp .env.example .env`
2. Start services: `docker compose up -d db redis`
3. Create and activate a virtual environment, then install:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\Activate.ps1
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Run migrations and create an admin account:
   ```bash
   python manage.py makemigrations pulse
   python manage.py migrate
   python manage.py createsuperuser
   ```
5. Start three processes in separate terminals (activate the same venv in each):
   ```bash
   python manage.py runserver
   celery -A pulse_project worker --loglevel=info
   celery -A pulse_project beat --loglevel=info
   ```
   Beat queues `pulse.tasks.check_prices` every 60 seconds. The worker performs notification logging asynchronously.

## Endpoints
Base URL: `http://127.0.0.1:8000`

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/api/auth/register/` | Public | Create account, return access token |
| POST | `/api/auth/login/` | Public | Authenticate and return access token |
| POST | `/api/alerts/` | JWT | Create alert for `request.user` |
| GET | `/api/alerts/` | JWT | List only the caller's alerts |
| DELETE | `/api/alerts/<id>/` | JWT | Set own alert to `inactive` |
| GET | `/api/flights/price/?route=DEL-BOM` | Public | Random mock price |
| GET | `/api/admin/summary/` | Admin-role JWT | Aggregate platform metrics |

For protected requests, send `Authorization: Bearer <access-token>`.

Register JSON:
```json
{"username":"alice","password":"securepass123","email":"alice@example.com"}
```
Create alert JSON:
```json
{"origin":"DEL","destination":"BOM","threshold_price":"4500.00"}
```

## Grant admin role for testing
Registration deliberately ignores any supplied role. Use Django admin or shell to grant it manually:
```bash
python manage.py shell
```
```python
from django.contrib.auth import get_user_model
from pulse.models import UserProfile
user = get_user_model().objects.get(username="alice")
user.profile.role = UserProfile.Role.ADMIN
user.profile.save()
```
Log in again and use the resulting access token.

## Tests
```bash
python manage.py test
```
The tests cover threshold comparisons, notification logging/status transition, user alert isolation, role safety, duplicate registration, login failure, mock prices and admin permissions.

## Mock routes
- DEL-BOM: ₹3,000–₹7,000
- BLR-HYD: ₹1,500–₹4,000
- DEL-BLR: ₹4,000–₹9,000
- BOM-GOA: ₹2,000–₹5,000

This is a simulated feed, not live airfare.

## Notes
- Notification delivery is represented by a database `NotificationLog`; email/SMS/push is not specified in the brief.
- Docker Compose runs PostgreSQL and Redis only; Django and Celery run on the host. If you containerize the app, `localhost` will no longer point to the host. Set `PRICE_FEED_URL` to a reachable service URL such as `http://web:8000/api/flights/price/` and configure Redis/database hosts accordingly.
- Production deployment requires a secure secret, restrictive allowed hosts, HTTPS and deployment-specific service settings.
