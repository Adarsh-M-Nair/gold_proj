# GoldSafe Django API

Phase 1 adds a Django REST API for customer onboarding and pledge records. It retains the existing Flask application while the frontend and deployment phases are completed.

## Local setup

From the repository root, install the root `requirements.txt`, then run:

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 backend/manage.py migrate
py -3.11 backend/manage.py import_legacy_sqlite
py -3.11 backend/manage.py test apps.pledges
py -3.11 backend/manage.py runserver
```

Without `DATABASE_URL`, Django uses the ignored local database at `backend/db.sqlite3`. To target PostgreSQL, set `DATABASE_URL` to a PostgreSQL connection URL before running migrations or the importer. The importer reads the repository's existing `customers.db` by default; pass `--source` to select another SQLite file. Re-running it skips pledge codes already imported.

## API

- `GET /api/v1/pledges/?search=<name|phone|aadhaar|pledge-code>&page=1&page_size=10`
- `GET /api/v1/pledges/<uuid>/`
- `DELETE /api/v1/pledges/<uuid>/` (soft delete)
- `POST /api/v1/uploads/` (multipart field `image`; local development storage, JPG/PNG/WEBP up to 10 MB)
- `POST /api/v1/onboarding/register-customer/`

List responses omit deleted pledges unless `status=DELETED` is requested. Aadhaar is searchable but only returned masked. Image metadata stores legacy paths as object keys until Phase 3 moves files to MinIO/S3.

## React frontend

From `frontend`, install dependencies and start the Vite development server:

```powershell
npm install
npm run dev
```

In another terminal, run the Django API at `http://127.0.0.1:8000`. Vite proxies `/api` and `/media` to Django. The frontend is available at `http://localhost:5173`.

The registration screen uploads validated image files to local Django media storage before submitting the onboarding request. This endpoint is for local development only; Phase 3 replaces it with private MinIO/S3 uploads. The jewellery identification page is ready for the matching API, but the current backend does not yet include matching endpoints; those are part of the ML service and pgvector phases.

This phase is a development migration, not a production security boundary. Authentication, role permissions, encrypted KYC storage, audit logging, private object storage, and a configured matching service remain required before production use.