# Global Services Technologie (GST)  Frontend

Responsive React/TypeScript frontend based on the supplied GST visual references. It contains the French public website and a separate, functional administration demonstration.

## Run locally

```bash
pnpm install
pnpm dev
```

Create a production bundle with:

```bash
pnpm build
```

## Routes

- `/`, `/a-propos`, `/references`, `/services`, `/contact`  public website
- `/admin/login`  demonstration login
- `/admin`  dashboard, requests, projects, services, reports, team and settings

The login accepts any non-empty email and password. It is intentionally a frontend-only demonstration and does not provide real authentication or access control.

## Structure

- `src/components`  shared public layout and content components
- `src/pages`  public pages
- `src/admin`  administrative application
- `src/data`  one consistent mock dataset
- `src/services`  asynchronous mock API, local persistence and CSV export
- `src/types`  domain types for inquiries, projects, services and users
- `public/assets`  reference imagery supplied with the project

## Future FastAPI connection

Set `VITE_API_BASE_URL` to the FastAPI origin. `src/services/mockApi.ts` exposes the current data boundary; replace its local-storage operations with JSON `fetch` calls to the configured `API_BASE_URL`. UI components do not contain embedded record datasets, so this migration does not require a page rewrite.

## Current limitations

- Authentication, authorization, email, uploads and shared multi-user persistence require the future backend.
- Changes are stored only in the current browser’s `localStorage`.
- Client and project names marked “exemple” are demonstration content, not verified GST references.
