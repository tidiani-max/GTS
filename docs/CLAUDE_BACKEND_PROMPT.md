# Claude task: Build and connect the GST backend to this existing frontend

You are working inside the **GST (Global Services Technologie)** project. The existing React 19 + TypeScript + Vite frontend is the approved UI and MUST be preserved. Read `README.md`, `src/App.tsx`, `src/admin/AdminApp.tsx`, `src/pages/PublicPages.tsx`, `src/data/mockData.ts`, `src/services/mockApi.ts`, and `src/types/index.ts` before changing code.

## Goal
Build a production-minded Python **FastAPI** backend and connect it to the existing frontend. Deliver a working full-stack project, not just an architecture proposal. Keep the existing design, public routes (`/`, `/a-propos`, `/references`, `/services`, `/contact`) and admin experience (`/admin/login`, `/admin/*`). If an admin function is missing or only a placeholder, implement it in the existing style.

## Backend and persistence
- Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic migrations, PostgreSQL.
- Secure password hashing; JWT access/refresh or another well-documented secure session strategy; role-based access control (at minimum super-admin, administrator, staff/read-only where appropriate).
- Environment-based configuration and validation. Never commit real secrets. Provide `.env.example`.
- REST API under `/api/v1`; OpenAPI docs; consistent validation/error responses; pagination, filtering, sorting and search for list endpoints.
- Models and migrations for admin users, inquiries/contact submissions, services, projects, clients, team members, internal notes, status history/audit events, notifications, and settings. Add media/file metadata only if the UI needs it.
- Seed command for clearly marked demo data. Avoid presenting example clients/projects as verified real GST customers.
- Add indexes and timestamps; use transactions where needed.

## Connect the frontend
- Keep the frontend look and existing UX intact. Replace `src/services/mockApi.ts` localStorage-only data operations with a typed API client using `VITE_API_BASE_URL` (document the exact env variable). Keep a mock/demo adapter only if useful for offline development, with a clear switch.
- Contact form submissions must POST to the backend and then appear in the admin inquiry list. Admin edits/status changes/notes/assignments/projects/services/users/settings must persist in PostgreSQL and refresh consistently across browsers.
- Add real login/logout, token/session handling, protected admin routes, and backend authorization. Do not treat a frontend-only route guard as security. Never store plain-text passwords.
- Add loading, empty, success and error states; avoid breaking the existing design. Handle expired sessions and unauthorized API responses safely.
- Include CORS configuration restricted by environment, request validation, rate limiting on public forms/authentication, safe upload handling if uploads are supported, and security headers where practical.

## Admin pages and workflow
Audit every admin page in the current frontend: dashboard, requests, projects, services, reports, team, settings and any additional modules already present. Make each major control functional. Add missing admin pages or controls when required to manage all backend data. Include search/filter/pagination, detail view, status and priority changes, assignment, internal notes, history/audit trail, CSV export and useful reporting. Dashboard KPIs/charts must be calculated from real API data, not hard-coded demo totals.

## Automation
Implement useful, configurable automationnot just buttons labelled “automate”:
- Background task system suitable for FastAPI (prefer a Redis-backed worker such as Celery/RQ/Arq if justified; otherwise use a clearly documented scheduler for lightweight jobs).
- Scheduled follow-up reminders for open inquiries with due dates; notifications for new submissions and overdue requests; periodic summary/report generation; cleanup of expired temporary files/tokens if applicable.
- Email notifications through SMTP/provider configuration, with a development console/log mode if credentials are absent. Never send mail in tests.
- Admin UI to view notification/job status and configure enable/disable, schedule, recipients and thresholds where useful.
- Retry/backoff, idempotency, logging and visible failures; no duplicate reminder spam. Include a dry-run mode and explain how to test jobs locally.
- Do not add risky unattended actions. Document which automations are enabled by default.

## Docker and quality
- Dockerfiles for frontend and backend, `docker-compose.yml` for frontend, FastAPI, PostgreSQL and any worker/Redis required.
- Persistent database volume, health checks, startup/migration instructions, seed instructions and graceful error handling.
- Add backend tests for auth/RBAC, contact submission, admin CRUD, status transitions, filters, and automation logic; add frontend/API integration checks where practical.
- Run migrations and tests; run frontend production build (`pnpm build` or npm equivalent). Fix all errors you introduce. Do not claim tests passed unless actually run.
- Add root README with exact Mac/Windows instructions, prerequisites, commands, local URLs, demo credentials created by seed, API docs URL, reset/backup notes, troubleshooting and production deployment cautions.

## Acceptance criteria
1. Existing public website and admin UI still work and visually match the supplied frontend.
2. Contact form data persists in PostgreSQL and appears in admin.
3. Real authentication and server-side role checks protect admin APIs.
4. Admin CRUD, status workflows, notes/history, charts and reports use backend data.
5. Automation can be demonstrated locally and its execution/logs can be inspected.
6. `docker compose up --build` starts the complete system from a clean checkout, followed by documented migrations/seeding if required.
7. No secrets or real credentials are committed; `.env.example` is complete.

Start by inspecting the existing app, then implement the backend and integration directly. Do not stop after writing a plan. At the end, summarize files changed, commands run, tests/build results, demo credentials, URLs and any genuine remaining limitations.
