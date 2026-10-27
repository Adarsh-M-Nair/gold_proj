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
- `GET /api/v1/catalogue/<category>/<item_id>/` (reference item details and image gallery)
- `GET /api/v1/catalogue/<category>/<item_id>/images/<filename>` (reference image)

List responses omit deleted pledges unless `status=DELETED` is requested. Aadhaar is searchable but only returned masked. Image metadata stores legacy paths as object keys until Phase 3 moves files to MinIO/S3.

## React frontend

From `frontend`, install dependencies and start the Vite development server:

```powershell
npm install
npm run dev
```

In another terminal, run the Django API at `http://127.0.0.1:8000`. Vite proxies `/api` and `/media` to Django. The frontend is available at `http://localhost:5173`.

The registration screen uploads validated image files to local Django media storage before submitting the onboarding request. This endpoint is for local development only; Phase 3 replaces it with private MinIO/S3 uploads.

## Phase 4 ML matching

Install the root `requirements.txt`, configure PostgreSQL with pgvector, and start the ML service as described in [`../ml_service/README.md`](../ml_service/README.md). Django forwards `POST /api/v1/matching/search/` image uploads to `ML_SERVICE_URL` (default `http://127.0.0.1:8001`) and returns the registered pledge records whose saved jewellery images are most similar, ranked by their best-matching image. Each pledge appears once, deleted pledges are excluded, and every result includes the pledge code, customer summary (masked Aadhaar), jewellery details, and image URLs.

When a customer is registered, each pledge image is embedded through the ML service and its `embedding_status` becomes `COMPLETED`, or `FAILED` if the file is missing or the ML service is unavailable (registration still succeeds). Index existing records, or retry failures, with:

```powershell
python manage.py index_pledge_images        # PENDING and FAILED images
python manage.py index_pledge_images --all  # re-embed everything, e.g. after changing EMBEDDING_MODEL_VERSION
```

Images imported from the legacy app with `static/uploads/...` keys are read from the repository's `static/uploads` folder.

This phase is a development migration, not a production security boundary. Authentication, role permissions, encrypted KYC storage, audit logging, private object storage, and a configured matching service remain required before production use.

Selecting an identification result opens the matched pledge's images and details, with a link to the full pledge record. The catalogue endpoints under `/api/v1/catalogue/` still serve the local `Dataset` reference images.