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
- `POST /api/v1/onboarding/register-customer/`

List responses omit deleted pledges unless `status=DELETED` is requested. Aadhaar is searchable but only returned masked. Image metadata stores legacy paths as object keys until Phase 3 moves files to MinIO/S3.

This phase is a development migration, not a production security boundary. Authentication, role permissions, encrypted KYC storage, audit logging, and private object storage remain required before production use.