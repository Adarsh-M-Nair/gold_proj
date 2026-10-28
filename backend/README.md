# GoldSafe Django API

Phase 1 adds a Django REST API for customer onboarding and pledge records. It retains the existing Flask application while the frontend and deployment phases are completed.

## Local setup

Start the `goldsafe-postgres` Docker container with port 5432 published on
`127.0.0.1`. From the repository root, copy `.env.example` to `.env` and replace
`YOUR_POSTGRES_PASSWORD` with the container's PostgreSQL password. URL-encode
special characters in the username and password. The root `.env` is ignored by
Git and loaded automatically by Django; existing environment variables take
precedence. If Django runs in Docker, use the PostgreSQL service hostname on its
Docker network instead of `127.0.0.1`.

Install the root `requirements.txt`, then run:

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 backend/manage.py migrate
py -3.11 backend/manage.py test apps.pledges
py -3.11 backend/manage.py runserver
```

Django requires a PostgreSQL `DATABASE_URL` and no longer falls back to SQLite.
Restart the Django server and Celery worker after changing `.env` or their
environment.
Verify the connection without printing credentials:

```powershell
py -3.11 backend/manage.py shell -c "from django.db import connection; from apps.customers.models import Customer; d = connection.settings_dict; print({k: d.get(k) for k in ('ENGINE', 'NAME', 'HOST', 'PORT')}); print('Customers:', Customer.objects.count())"
```

Switching databases does not copy existing SQLite records. Existing SQLite files
are left untouched. If you intentionally want to import the legacy Flask data,
run `py -3.11 backend/manage.py import_legacy_sqlite`. The importer reads the
repository's `customers.db` by default; `--source` must point to a database with
the legacy Flask schema, not Django's `backend/db.sqlite3`. Re-running it skips
pledge codes already imported.

## API

- `GET /api/v1/pledges/?search=<name|phone|aadhaar|pledge-code>&page=1&page_size=10`
- `GET /api/v1/pledges/<uuid>/`
- `DELETE /api/v1/pledges/<uuid>/` (soft delete)
- `POST /api/v1/uploads/presign/` (JSON: `filename`, `content_type`, `file_size_bytes`)
- `POST /api/v1/uploads/` (multipart field `image`; local-development upload fallback)
- `GET /api/v1/images/access/<signed-token>/` (short-lived private image access)
- `POST /api/v1/onboarding/register-customer/`
- `GET /api/v1/catalogue/<category>/<item_id>/` (reference item details and image gallery)
- `GET /api/v1/catalogue/<category>/<item_id>/images/<filename>` (reference image)

List responses omit deleted pledges unless `status=DELETED` is requested. Aadhaar
is searchable but only returned masked. New pledge images are private; API
responses provide short-lived access URLs rather than object keys. Existing
legacy image paths continue to be read from `static/uploads/`.

## React frontend

From `frontend`, install dependencies and start the Vite development server:

```powershell
npm install
npm run dev
```

In another terminal, run the Django API at `http://127.0.0.1:8000`. Vite proxies `/api` to Django. The frontend is available at `http://localhost:5173`.

Configure `OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_ENDPOINT_URL`,
`OBJECT_STORAGE_ACCESS_KEY`, `OBJECT_STORAGE_SECRET_KEY`, and
`OBJECT_STORAGE_REGION` to use a private S3-compatible bucket (MinIO locally or
S3 in production). Set `OBJECT_STORAGE_ADDRESSING_STYLE=path` for MinIO. Keep
public/anonymous bucket access disabled. For browser uploads, configure bucket
CORS to allow the frontend origin and `POST` requests. Without an
object-storage bucket, Django uses local media storage and
the upload API proxies the file for development; images are still served
through expiring signed API URLs.

Example MinIO and Redis configuration for the root `.env`:

```dotenv
OBJECT_STORAGE_BUCKET=goldsafe-private
OBJECT_STORAGE_ENDPOINT_URL=http://127.0.0.1:9000
OBJECT_STORAGE_ACCESS_KEY=replace-with-minio-access-key
OBJECT_STORAGE_SECRET_KEY=replace-with-minio-secret-key
OBJECT_STORAGE_REGION=us-east-1
OBJECT_STORAGE_ADDRESSING_STYLE=path
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
```

Set `CELERY_BROKER_URL` to the Redis broker URL (defaults to
`redis://127.0.0.1:6379/0`). Start a worker from the `backend` directory:

```powershell
py -3.11 -m celery -A config worker --loglevel=info
```

Registration verifies the uploaded bytes, size, actual image type, and SHA-256
checksum before creating records. Celery generates a 512-pixel WebP thumbnail
and submits the embedding request after the database transaction commits.
Processing failures are marked `FAILED` and can be retried with the existing
`index_pledge_images` management command.

## Phase 4 ML matching

Install the root `requirements.txt`, configure PostgreSQL with pgvector, and start the ML service as described in [`../ml_service/README.md`](../ml_service/README.md). Django forwards `POST /api/v1/matching/search/` image uploads to `ML_SERVICE_URL` (default `http://127.0.0.1:8001`) and returns the registered pledge records whose saved jewellery images are most similar, ranked by their best-matching image. Each pledge appears once, deleted pledges are excluded, and every result includes the pledge code, customer summary (masked Aadhaar), jewellery details, and image URLs.

When a customer is registered, a Celery worker embeds each pledge image through
the ML service and updates its `embedding_status` to `COMPLETED` or `FAILED`
without blocking registration. Index existing records, or retry failures, with:

```powershell
python manage.py index_pledge_images        # PENDING and FAILED images
python manage.py index_pledge_images --all  # re-embed everything, e.g. after changing EMBEDDING_MODEL_VERSION
```

Images imported from the legacy app with `static/uploads/...` keys are read from the repository's `static/uploads` folder.

This phase is a development migration, not a production security boundary.
Authentication, role permissions, encrypted KYC storage, audit logging, and a
configured matching service remain required before production use.

Selecting an identification result opens the matched pledge's images and details, with a link to the full pledge record. The catalogue endpoints under `/api/v1/catalogue/` still serve the local `Dataset` reference images.