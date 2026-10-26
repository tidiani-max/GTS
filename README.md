# GST  Site public + Administration (Full-stack)

React 19 + Vite frontend (design inchangé) · **FastAPI** + SQLAlchemy 2 + Alembic · **PostgreSQL 16** · worker d'automatisation.

```
GST-Fullstack/
├── frontend/   React app (public site + /admin), nginx.conf, Dockerfile
├── backend/    FastAPI app, Alembic migrations, seed, worker, tests, Dockerfile
├── docs/       Original task prompt
└── docker-compose.yml   db + api + worker + frontend
```

## 1. Quick start with Docker (recommended)

Prerequisites: **Docker Desktop** (Mac or Windows, with Compose v2).

**Mac (Terminal)**
```bash
cd GST-Fullstack
cp .env.example .env
docker compose up --build
# in a second terminal, once (demo data + first admin):
docker compose exec api python -m app.seed
```
**Windows (PowerShell)**
```powershell
cd GST-Fullstack
copy .env.example .env
docker compose up --build
# in a second PowerShell window, once:
docker compose exec api python -m app.seed
```
Migrations run automatically when the `api` container starts.

| What | URL |
|---|---|
| Public site | http://localhost:8080 |
| Admin login | http://localhost:8080/admin/login |
| API (Swagger/OpenAPI) | http://localhost:8000/api/v1/docs |
| Health check | http://localhost:8000/api/v1/health |

**Demo credentials (created by the seed  change them!)**

| Account | Password | Role |
|---|---|---|
| `admin@gst-demo.ml` | `ChangeMe!2025` | super_admin |
| `fatou@example.com` | `ChangeMe!2025` | admin |
| `ibrahim@example.com`, `amadou@example.com` | `ChangeMe!2025` | staff |
| `lecteur@example.com` | `ChangeMe!2025` | readonly |

Seeded clients, inquiries and projects are **fictional demo records** (flagged `DÉMO` in the UI, `example.com` emails). `python -m app.seed --no-demo` creates only the admin account, settings and the service catalogue.

## 2. Local development without Docker

Prerequisites: Python 3.12+, Node 22+, pnpm (`npm i -g pnpm`), a running PostgreSQL 16 with a `gst` database/user.

```bash
# Backend  (Windows: use  py -m venv .venv  and  .venv\Scripts\activate)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # edit DATABASE_URL if needed
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
python -m app.worker            # optional, separate terminal: scheduled automation

# Frontend (new terminal)
cd frontend
pnpm install
pnpm dev                        # http://localhost:8443
```
**Frontend ↔ backend:** the only setting is `VITE_API_BASE_URL` (see `frontend/.env.example`; `.env.development` points to `http://localhost:8000/api/v1`; Docker builds use `/api/v1` through nginx). The default CORS list already allows `http://localhost:8443` and `http://localhost:8080`.

## 3. What was built

* **Auth**: Argon2id password hashes; short-lived JWT access token (kept in memory only) + rotating httpOnly refresh cookie with re-use detection; account lock-out after 5 failures (15 min); login rate limit; password policy; sessions revoked on password reset/deactivation. Expired sessions send the user back to the login page with a notice.
* **RBAC (enforced server-side on every route)**

| Capability | readonly | staff | admin | super_admin |
|---|:-:|:-:|:-:|:-:|
| View inquiries/projects/services/reports/team | ✔ | ✔ | ✔ | ✔ |
| Update inquiry (status, priority, assignee, notes) / update project | | ✔ | ✔ | ✔ |
| Create/delete project, edit services, delete inquiry, company settings, automation, audit log | | | ✔ | ✔ |
| Manage users and roles | | | | ✔ |
* **Inquiries**: public form → PostgreSQL → admin list. Server-side search, filters (status, priority, assignee, overdue), sorting, pagination, detail drawer, status workflow (invalid transitions rejected), assignment, internal notes, history/audit trail, CSV export (formula-injection safe). Honeypot + de-duplication + rate limit (5 / 10 min / IP) on the public form.
* **Projects, services, team/users, settings, notifications, reports** all read/write the database. Dashboard and report KPIs/charts are computed from real data. The contact form only offers *active* services from the catalogue.
* **Audit**: every create/update/delete/assignment/status change/login is recorded (`GET /api/v1/audit`, admin+).
* **API**: `/api/v1`, OpenAPI docs, uniform error envelope `{"error": {"code","message","details"}}`, security headers, CORS restricted by env, config validated at start-up (production refuses weak secrets / insecure cookies).

## 4. Automation

A dedicated **worker** process (`python -m app.worker`, own container) runs a simple scheduler loop (30 s tick). No Redis: volumes are small and each job is idempotent through DB de-duplication keys; a PostgreSQL advisory lock prevents two workers running jobs at once. Admin UI: **Admin → Automatisation** (jobs, run log, email outbox, configuration, *Simuler* / *Exécuter*).

| Job | Default | Behaviour |
|---|---|---|
| New-inquiry alert | **on** | Event-driven at submission: in-app notification + queued email to admins (honours each user's preferences). |
| `follow_up_reminders` | **on**, every 60 min | Open inquiries whose follow-up date is due (lead days configurable); max 5 reminders, ≥ 24 h apart, to the assignee (or admins). Changing the follow-up date resets the counter. |
| `overdue_alerts` | **on**, every 6 h | **One digest per day** for open inquiries past their follow-up date (no per-inquiry spam). |
| `send_emails` | **on**, every minute | Sends the email outbox with retry + exponential backoff (max 5 attempts); failures are visible. |
| `weekly_summary` | **on**, Monday 07:00 UTC | Activity summary to admins (once per ISO week). |
| `cleanup` | **on**, daily | Deletes expired/revoked refresh tokens and old read notifications, sent emails and job runs (retention 90 days). Audit events are never deleted. |

No unattended destructive business action exists (nothing closes/deletes inquiries automatically). **Email**: `EMAIL_MODE=console` (default) only logs messages; set `smtp` + `SMTP_*` for real delivery. Tests never send mail.

**Test locally**
1. Open Admin → Automatisation → *Simuler* on a job (dry-run: reports what it would do, changes nothing), then *Exécuter*.
2. Create an inquiry (contact form), set its follow-up to today in the drawer, run `follow_up_reminders`; check the bell and the *Emails* tab. Run it again: nothing is duplicated.
3. Logs: `docker compose logs -f worker` (console emails appear in the `worker` logs). API equivalents: `POST /api/v1/automation/jobs/{name}/run?dry_run=true`.
4. *Mode simulation global* (Configuration tab) makes the scheduled worker simulate only.

## 5. Tests and checks

```bash
cd backend
pytest -q                                   # SQLite, no setup needed
TEST_DATABASE_URL=postgresql+psycopg://gst:gst@localhost:5432/gst_test pytest -q   # PostgreSQL
cd ../frontend && pnpm build                # type-check + production build
```
Tests drop all tables, so they ignore `DATABASE_URL` and only use `TEST_DATABASE_URL` or SQLite. They cover auth/RBAC, contact submission, admin CRUD, status transitions, filters/search/pagination, CSV, reports and automation (38 tests).

## 6. Operations

* **Backup**: `docker compose exec db pg_dump -U gst gst > backup.sql` · **Restore**: `docker compose exec -T db psql -U gst gst < backup.sql`
* **Reset everything (deletes all data)**: `docker compose down -v` then `up --build` and seed again.
* **New migration** after changing models: `alembic revision --autogenerate -m "msg"` then `alembic upgrade head`.
* **Troubleshooting**: `api` unhealthy → `docker compose logs api` (invalid env values are reported at start-up). Port in use → change the left side of `ports:` in `docker-compose.yml`. Login fails with CORS/cookie errors in dev → open the site via `localhost` (not `127.0.0.1`) and keep the origin in `CORS_ORIGINS`. Locked account → wait 15 min or reset the password as super-admin.

## 7. Before going to production

* Set `ENVIRONMENT=production`, a random `SECRET_KEY` (≥ 32 chars), `COOKIE_SECURE=true`, your real `CORS_ORIGINS`, strong `POSTGRES_PASSWORD`; serve over **HTTPS** (reverse proxy / load balancer) and don't publish the DB or API ports.
* **Do not run the seed with demo data**; change/remove `admin@gst-demo.ml` and the shared demo password immediately (or seed with `--no-demo` and a strong `SEED_ADMIN_PASSWORD`).
* The rate limiter is in-process (per replica); with several API replicas add limits at the proxy or move it to Redis.
* Configure SMTP and test delivery; schedule off-site database backups; monitor `/api/v1/health` and the worker logs.

## 8. Known limitations

* Docker images/compose were written but **not built in the authoring sandbox** (no Docker there); the same code was run against a real PostgreSQL 16 (migrations, seed, API, worker, 38 tests) and the frontend production build succeeded. Run `docker compose up --build` once on your machine to confirm.
* The admin UI was type-checked and built but not clicked through in a real browser during authoring; the API calls it makes were exercised by the backend tests and live requests.
* Concurrent edits are last-write-wins (lists refresh every 30 s and on window focus). No file uploads exist (not needed by the UI). Team members and admin users are one table.
