# GoldSafe — Revised Implementation Plan

## 1. Purpose of Revision

This plan updates the original GoldSafe implementation to match the uploaded wireframes and the current Flask prototype while migrating the system to an enterprise-ready stack.

The current Flask application uses:

```text
gold_proj/
├── app.py
├── database.py
├── customers.db
├── item_embeddings.npy
├── Dataset/
├── ml/
│   ├── feature_extraction.py
│   └── similarity.py
├── static/uploads/
└── templates/
    ├── index.html
    ├── register.html
    ├── register_success.html
    ├── customers.html
    └── results.html
```

The revised implementation retains the same user journey and screen structure but replaces the Flask monolith, SQLite database, local image uploads, and NumPy-based similarity search with a modular production-oriented architecture.

## 2. Current Wireframe Flow

The wireframes define three primary user flows:

### 2.1 Dashboard and Pledge Records

The dashboard displays:

- GoldSafe branding: **GoldSafe — Mythic Finance AI**
- Total pledges counter
- System status indicator
- Search bar for customer records
- **Register Customer** action
- Pledge records table

The pledge records table contains:

| Column | Description |
|---|---|
| Pledge ID | System-generated ID, for example `GS-2026-0008` |
| Photo | Captured ornament photo thumbnail |
| Customer Name | Registered customer name |
| Phone | Customer phone number |
| Aadhaar | Customer Aadhaar number |
| Registered | Customer/pledge registration timestamp |
| Delete | Delete action for the record |

The search field supports lookup by:

- Customer name
- Phone number
- Aadhaar number

### 2.2 Client Onboarding

The **Register New Customer** screen captures:

- Customer full name
- Phone number
- Aadhaar number
- Multi-angle pledged-ornament photographs

It provides two image-capture methods:

- Webcam capture with zoom
- Multi-select file upload

The screen explicitly states that the customer KYC details and live ornament photographs are used to create a customer pledge account.

### 2.3 Jewellery Identification

The **Vision Match Engine** screen supports:

- Image upload through drag-and-drop or file browsing
- Live camera capture
- Supported formats: JPG, PNG, WEBP
- A **Find Similar Items** action
- User guidance for dark, non-reflective backgrounds and clear lighting

The interface identifies the current ML approach as **ResNet-50 Ready** and describes the operation as deep neural feature extraction against Muthoot’s reference ornament dataset.

## 3. Target Technology Stack

| Layer | Current Flask Implementation | Revised Enterprise Implementation |
|---|---|---|
| Backend | Flask monolith | Django 5.x + Django REST Framework |
| Database | SQLite `customers.db` | PostgreSQL 16 with pgvector |
| ORM / migrations | Custom `database.py` | Django ORM and migrations |
| Image storage | `static/uploads/` | MinIO locally, Amazon S3 in production |
| Embeddings | `item_embeddings.npy` | pgvector vector column |
| Similarity search | NumPy cosine similarity | pgvector cosine-distance search |
| ML logic | `ml/feature_extraction.py`, `ml/similarity.py` | Separate FastAPI ML microservice |
| Background jobs | Synchronous processing | Celery + Redis |
| Frontend | Jinja templates | React 18 + TypeScript SPA |
| Styling | HTML/CSS templates | Tailwind CSS |
| API communication | Flask form posts | REST APIs using Axios |
| Authentication | Not visible in prototype | JWT + role-based access control |
| Deployment | Local Flask server | Docker Compose, Nginx, Gunicorn, Uvicorn |

## 4. Revised System Architecture

```text
React Frontend
      |
      | REST / JWT
      v
Django + DRF API
      |
      +--------------------+---------------------+
      |                    |                     |
      v                    v                     v
PostgreSQL + pgvector   MinIO / S3         Celery + Redis
Customer & pledge data  Ornament images        |
                                               v
                                        FastAPI ML Service
                                               |
                                    ResNet-50 / embedding model
```

### 4.1 Service responsibilities

| Service | Responsibility |
|---|---|
| React frontend | Dashboard, customer registration, pledge records, image capture, jewellery identification, result display |
| Django + DRF | Customer KYC, pledge records, image metadata, search, deletion, audit logs, authentication |
| PostgreSQL + pgvector | Structured records, image metadata, embeddings, vector search |
| MinIO / S3 | Original ornament images, thumbnails, secure object storage |
| FastAPI ML service | Image validation, preprocessing, ResNet-50 feature extraction, embedding generation |
| Celery + Redis | Asynchronous embedding generation, thumbnail creation, cleanup tasks |

## 5. Mapping Flask Prototype to New Stack

### 5.1 Flask template mapping

| Current Flask Template | Revised React Page | Route |
|---|---|---|
| `index.html` | Dashboard | `/` |
| `register.html` | Register Customer | `/register` |
| `register_success.html` | Registration success state or toast | Part of `/register` |
| `customers.html` | Pledge Records | `/pledges` |
| `results.html` | Jewellery Identification Results | `/identify/results/:searchId` |
| Vision Match Engine screen | Jewellery Identification | `/identify` |

### 5.2 Flask module mapping

| Current Flask Component | Revised Component |
|---|---|
| `app.py` | Django project, DRF routers, serializers, views |
| `database.py` | Django models, migrations, database configuration |
| `customers.db` | PostgreSQL database |
| `static/uploads/` | MinIO/S3 object storage |
| `item_embeddings.npy` | `jewellery_embeddings` table with pgvector embedding column |
| `ml/feature_extraction.py` | FastAPI `/embed` endpoint |
| `ml/similarity.py` | pgvector similarity query and FastAPI ranking helper |
| `Dataset/` | Reference image dataset used for model evaluation and optional fine-tuning |
| Jinja form handling | React forms + DRF serializers |
| Direct image rendering | Presigned image URLs from MinIO/S3 |

## 6. Revised Frontend Structure

```text
frontend/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── router.tsx
│   │   └── providers.tsx
│   │
│   ├── pages/
│   │   ├── DashboardPage.tsx
│   │   ├── RegisterCustomerPage.tsx
│   │   ├── PledgeRecordsPage.tsx
│   │   ├── JewelleryIdentificationPage.tsx
│   │   ├── MatchResultsPage.tsx
│   │   └── NotFoundPage.tsx
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx
│   │   │   ├── Header.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── dashboard/
│   │   │   ├── StatCard.tsx
│   │   │   ├── SystemStatusCard.tsx
│   │   │   └── SearchBar.tsx
│   │   ├── customers/
│   │   │   ├── CustomerForm.tsx
│   │   │   ├── KycFields.tsx
│   │   │   └── CustomerTable.tsx
│   │   ├── jewellery/
│   │   │   ├── WebcamCapture.tsx
│   │   │   ├── MultiImageUploader.tsx
│   │   │   ├── ImagePreviewGrid.tsx
│   │   │   └── MatchResultCard.tsx
│   │   └── common/
│   │       ├── Button.tsx
│   │       ├── Input.tsx
│   │       ├── Modal.tsx
│   │       ├── Table.tsx
│   │       ├── Badge.tsx
│   │       └── Spinner.tsx
│   │
│   ├── services/
│   │   ├── apiClient.ts
│   │   ├── authService.ts
│   │   ├── customerService.ts
│   │   ├── pledgeService.ts
│   │   ├── imageService.ts
│   │   └── matchingService.ts
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useWebcam.ts
│   │   ├── useImageUpload.ts
│   │   └── useDebounce.ts
│   │
│   ├── types/
│   │   ├── customer.ts
│   │   ├── pledge.ts
│   │   ├── jewellery.ts
│   │   └── matching.ts
│   │
│   └── utils/
│       ├── validation.ts
│       ├── formatting.ts
│       └── imageUtils.ts
│
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── Dockerfile
```

## 7. Frontend Screens and Wireframe Mapping

### 7.1 Dashboard — `/`

This page replaces `index.html`.

**Wireframe elements:**

- GoldSafe header and branding
- Total pledges statistic
- System status indicator
- Search bar
- Register Customer button
- Pledge records preview

**React implementation:**

- `DashboardPage.tsx`
- `StatCard.tsx` for total pledges
- `SystemStatusCard.tsx` for backend, database, ML-service, and storage status
- `SearchBar.tsx` for name, phone, and Aadhaar search
- Quick-action button routing to `/register`
- Recent pledges table or pledge summary cards

**API calls:**

```http
GET /api/v1/dashboard/summary/
GET /api/v1/pledges/?search=<query>&page=1
GET /api/v1/system/health/
```

### 7.2 Register Customer — `/register`

This page replaces `register.html` and `register_success.html`.

**Wireframe fields:**

| Field | Required | Validation |
|---|---|---|
| Customer Full Name | Yes | Non-empty, reasonable length |
| Phone Number | Yes | 10-digit Indian mobile number |
| Aadhaar Number | Yes | 12-digit Aadhaar format, masked in UI where appropriate |
| Ornament Photos | Yes | At least one image; multiple angles recommended |

**Capture options:**

- Webcam capture with zoom control
- Multi-select file upload
- Image preview and removal before submission
- Optional image-quality warning for blur, darkness, or low resolution

**React implementation:**

- `RegisterCustomerPage.tsx`
- `CustomerForm.tsx`
- `KycFields.tsx`
- `WebcamCapture.tsx`
- `MultiImageUploader.tsx`
- `ImagePreviewGrid.tsx`

**Submission flow:**

1. React validates the form.
2. React requests presigned upload URLs from Django.
3. React uploads each image directly to MinIO/S3.
4. React submits customer and image references to Django.
5. Django creates customer, pledge, jewellery item, and jewellery image records.
6. Celery triggers embedding generation.
7. The UI shows a success state and redirects to the pledge record or dashboard.

**API calls:**

```http
POST /api/v1/uploads/presign/
POST /api/v1/customers/
POST /api/v1/pledges/
POST /api/v1/jewellery-items/
POST /api/v1/jewellery-images/bulk/
```

Alternatively, expose one transactional onboarding endpoint:

```http
POST /api/v1/onboarding/register-customer/
```

### 7.3 Pledge Records — `/pledges`

This page replaces `customers.html`.

**Wireframe table columns:**

| UI Column | Database Source |
|---|---|
| Pledge ID | `pledges.pledge_code` |
| Photo | Primary `jewellery_images.thumbnail_url` |
| Customer Name | `customers.full_name` |
| Phone | `customers.phone_number` |
| Aadhaar | `customers.aadhaar_number` |
| Registered | `customers.created_at` or `pledges.created_at` |
| Delete | Delete pledge/customer record action |

**Features:**

- Search by name, phone, or Aadhaar
- Pagination
- Sort by registration date
- View pledge details
- Delete record with confirmation modal
- Display pledge status badge
- Show embedding-generation status

**API calls:**

```http
GET /api/v1/pledges/?search=&page=&page_size=
GET /api/v1/pledges/{id}/
DELETE /api/v1/pledges/{id}/
```

### 7.4 Jewellery Identification — `/identify`

This page corresponds to the **Vision Match Engine** screen.

**Wireframe elements:**

- Header: **Vision Match Engine**
- Model badge: **ResNet-50 Ready**
- Image Upload tab
- Live Camera tab
- Drag-and-drop upload area
- Supported formats: JPG, PNG, WEBP
- **Find Similar Items** button
- Capture guidance message

**React implementation:**

- `JewelleryIdentificationPage.tsx`
- `MultiImageUploader.tsx`
- `WebcamCapture.tsx`
- `ImagePreviewGrid.tsx`
- `MatchResultCard.tsx`

**User flow:**

1. Staff uploads an ornament image or captures it using the webcam.
2. React displays a preview and allows the user to remove or replace the image.
3. React uploads the query image through a presigned URL.
4. React calls the matching endpoint.
5. Django sends the image reference to the ML service through Celery or synchronously for a low-latency interactive search.
6. The ML service generates a ResNet-50 embedding.
7. pgvector returns the top similar stored jewellery embeddings.
8. React displays ranked matches with similarity scores and stored images.

**API calls:**

```http
POST /api/v1/uploads/presign/
POST /api/v1/matching/search/
GET /api/v1/matching/search/{search_id}/
```

### 7.5 Match Results — `/identify/results/:searchId`

This page replaces `results.html`.

**Display elements:**

- Query image preview
- Search status: processing, completed, or failed
- Number of matches found
- Ranked match cards
- Similarity score
- Stored ornament image
- Pledge ID
- Customer name
- Phone and masked Aadhaar
- Registration date
- Optional actions: view pledge, confirm match, flag mismatch

**API calls:**

```http
GET /api/v1/matching/search/{search_id}/
GET /api/v1/pledges/{pledge_id}/
PATCH /api/v1/matching/results/{result_id}/review/
```

## 8. Revised Backend Structure

```text
backend/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── celery.py
│   ├── asgi.py
│   └── wsgi.py
│
├── apps/
│   ├── accounts/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── permissions.py
│   │   └── urls.py
│   │
│   ├── customers/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── validators.py
│   │   └── urls.py
│   │
│   ├── pledges/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── services.py
│   │   └── urls.py
│   │
│   ├── jewellery/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── services.py
│   │   └── urls.py
│   │
│   ├── uploads/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── storage.py
│   │   └── urls.py
│   │
│   ├── matching/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── services.py
│   │   ├── tasks.py
│   │   └── urls.py
│   │
│   ├── dashboard/
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   └── audit/
│       ├── models.py
│       ├── services.py
│       └── signals.py
│
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
└── manage.py
```

## 9. Revised Database Design

### 9.1 Core models

```text
StaffUser
Customer
Pledge
JewelleryItem
JewelleryImage
JewelleryEmbedding
MatchSearch
MatchResult
AuditLog
```

The wireframes combine customer registration and pledge creation into one onboarding flow. Therefore, the backend should support a transactional onboarding service that creates related records together.

### 9.2 `customers`

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| full_name | VARCHAR(255) | Required |
| phone_number | VARCHAR(15) | Required, indexed |
| aadhaar_number | VARCHAR(14) | Required, encrypted or hashed based on compliance policy |
| photo_url | VARCHAR | Optional customer photo |
| status | ENUM | ACTIVE, INACTIVE, DELETED |
| created_at | TIMESTAMP | Auto |
| updated_at | TIMESTAMP | Auto |

### 9.3 `pledges`

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| pledge_code | VARCHAR(20) | Human-readable ID, for example `GS-2026-0008` |
| customer_id | UUID | FK to customer |
| branch_id | UUID | FK to branch |
| pledge_date | DATE | Date of pledge |
| status | ENUM | ACTIVE, CLOSED, RE_PLEDGED, DELETED, FLAGGED |
| total_weight_grams | DECIMAL | Optional |
| estimated_value | DECIMAL | Optional |
| created_by | UUID | Staff user |
| created_at | TIMESTAMP | Auto |
| updated_at | TIMESTAMP | Auto |

The wireframe displays `GS-2026-0008`-style IDs, so `pledge_code` should be generated using a yearly sequence:

```text
GS-<YYYY>-<sequence>
```

### 9.4 `jewellery_items`

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| pledge_id | UUID | FK to pledge |
| category | VARCHAR | Optional |
| description | TEXT | Optional staff description |
| weight_grams | DECIMAL | Optional |
| purity | VARCHAR | Optional |
| status | ENUM | ACTIVE, RETURNED, FLAGGED |
| created_at | TIMESTAMP | Auto |

### 9.5 `jewellery_images`

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| jewellery_item_id | UUID | FK to jewellery item |
| pledge_id | UUID | Denormalized FK for faster queries |
| object_key | VARCHAR | MinIO/S3 object key |
| thumbnail_object_key | VARCHAR | Thumbnail object key |
| original_filename | VARCHAR | Original filename |
| content_type | VARCHAR | image/jpeg, image/png, image/webp |
| file_size_bytes | BIGINT | Uploaded file size |
| checksum_sha256 | VARCHAR | Integrity hash |
| capture_source | ENUM | WEBCAM, UPLOAD |
| image_type | ENUM | FRONT, BACK, SIDE, CLOSEUP, OTHER |
| embedding_status | ENUM | PENDING, PROCESSING, COMPLETED, FAILED |
| uploaded_by | UUID | Staff user |
| created_at | TIMESTAMP | Auto |

### 9.6 `jewellery_embeddings`

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| jewellery_image_id | UUID | FK to jewellery image |
| embedding | VECTOR(2048) | ResNet-50 embedding or selected model dimension |
| model_name | VARCHAR | For example, `resnet50-v1` |
| model_version | VARCHAR | Model release version |
| created_at | TIMESTAMP | Auto |

Use a pgvector index for cosine-distance search:

```sql
CREATE INDEX jewellery_embedding_cosine_idx
ON jewellery_embeddings
USING hnsw (embedding vector_cosine_ops);
```

### 9.7 `match_searches`

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| branch_id | UUID | Branch initiating search |
| query_image_id | UUID | Uploaded query image |
| status | ENUM | PENDING, PROCESSING, COMPLETED, FAILED |
| top_k | INTEGER | Number of matches requested |
| similarity_threshold | FLOAT | Minimum accepted similarity |
| searched_by | UUID | Staff user |
| created_at | TIMESTAMP | Auto |
| completed_at | TIMESTAMP | Nullable |

### 9.8 `match_results`

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| match_search_id | UUID | FK to match search |
| matched_jewellery_image_id | UUID | Stored image matched |
| matched_jewellery_item_id | UUID | Stored jewellery item |
| matched_pledge_id | UUID | Stored pledge |
| matched_customer_id | UUID | Stored customer |
| similarity_score | FLOAT | Cosine similarity |
| rank | INTEGER | Match rank |
| status | ENUM | PENDING, CONFIRMED, REJECTED, FLAGGED |
| reviewed_by | UUID | Nullable staff user |
| reviewed_at | TIMESTAMP | Nullable |

## 10. Revised API Design

### 10.1 Dashboard APIs

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/dashboard/summary/` | Total pledges, recent pledges, system status |
| GET | `/api/v1/system/health/` | Database, storage, Celery, and ML-service health |

Example response:

```json
{
  "total_pledges": 6,
  "recent_pledges": 2,
  "system_status": {
    "api": "ONLINE",
    "database": "ONLINE",
    "object_storage": "ONLINE",
    "ml_service": "ONLINE",
    "worker": "ONLINE"
  }
}
```

### 10.2 Customer and pledge APIs

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/customers/` | Create customer |
| GET | `/api/v1/customers/` | Search customers |
| GET | `/api/v1/customers/{id}/` | Get customer |
| PATCH | `/api/v1/customers/{id}/` | Update customer |
| POST | `/api/v1/onboarding/register-customer/` | Create customer, pledge, jewellery item, and image records |
| GET | `/api/v1/pledges/` | List and search pledges |
| GET | `/api/v1/pledges/{id}/` | Get pledge details |
| DELETE | `/api/v1/pledges/{id}/` | Soft-delete or archive pledge |
| GET | `/api/v1/pledges/{id}/images/` | Get pledge images |

### 10.3 Search parameters

```http
GET /api/v1/pledges/?search=adarsh
GET /api/v1/pledges/?search=9446585673
GET /api/v1/pledges/?search=781738707814
GET /api/v1/pledges/?status=ACTIVE&page=1&page_size=10
```

The `search` parameter should query:

- `customer__full_name__icontains`
- `customer__phone_number__icontains`
- `customer__aadhaar_number__icontains`
- `pledge_code__icontains`

### 10.4 Image upload APIs

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/uploads/presign/` | Get presigned upload URL |
| POST | `/api/v1/jewellery-images/` | Register uploaded image metadata |
| POST | `/api/v1/jewellery-images/bulk/` | Register multiple uploaded images |
| GET | `/api/v1/jewellery-images/{id}/download-url/` | Get short-lived image access URL |

### 10.5 Matching APIs

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/matching/search/` | Start jewellery similarity search |
| GET | `/api/v1/matching/search/{search_id}/` | Get search status and results |
| PATCH | `/api/v1/matching/results/{result_id}/review/` | Confirm, reject, or flag a match |
| GET | `/api/v1/matching/history/` | Get previous searches |

### 10.6 Example onboarding request

```json
{
  "customer": {
    "full_name": "Adarsh M. Nair",
    "phone_number": "9446585673",
    "aadhaar_number": "781738707814"
  },
  "pledge": {
    "branch_id": "8f3b6d1e-2b7a-4f5a-9c1d-7a9e6b2f4c10",
    "pledge_date": "2026-10-26",
    "total_weight_grams": 12.45,
    "estimated_value": 85000
  },
  "jewellery_item": {
    "category": "CHAIN",
    "description": "Gold chain with pendant",
    "purity": "22K"
  },
  "images": [
    {
      "object_key": "pledges/2026/10/abc-front.jpg",
      "content_type": "image/jpeg",
      "file_size_bytes": 842133,
      "checksum_sha256": "9f2c...",
      "capture_source": "WEBCAM",
      "image_type": "FRONT"
    },
    {
      "object_key": "pledges/2026/10/abc-side.jpg",
      "content_type": "image/jpeg",
      "file_size_bytes": 791204,
      "checksum_sha256": "1b7d...",
      "capture_source": "WEBCAM",
      "image_type": "SIDE"
    }
  ]
}
```

### 10.7 Example matching response

```json
{
  "search_id": "b1e9f4b2-1a2c-4d3e-8f90-2b6d7c8e9f10",
  "status": "COMPLETED",
  "query_image_url": "https://storage.example.com/query/xyz.jpg",
  "matches": [
    {
      "result_id": "2a7f...",
      "rank": 1,
      "similarity_score": 0.93,
      "pledge_id": "GS-2026-0008",
      "customer_name": "Adarsh M. Nair",
      "phone_number": "9446585673",
      "masked_aadhaar": "XXXX XXXX 7814",
      "registered_at": "2026-10-22T21:54:28Z",
      "stored_image_url": "https://storage.example.com/pledges/abc-front.jpg",
      "jewellery_description": "Gold chain with pendant"
    }
  ]
}
```

## 11. Migration From Flask

### 11.1 Database migration

1. Export records from `customers.db`.
2. Map Flask database fields to Django model fields.
3. Migrate customer names, phone numbers, Aadhaar numbers, registration timestamps, and pledge IDs.
4. Upload images from `static/uploads/` to MinIO/S3.
5. Generate thumbnails and SHA-256 checksums.
6. Regenerate embeddings using the FastAPI service.
7. Store embeddings in PostgreSQL pgvector.
8. Validate migrated records against the Flask application.

### 11.2 ML migration

| Current File | New Location | Change |
|---|---|---|
| `ml/feature_extraction.py` | `ml_service/app/embeddings.py` | Expose embedding generation through FastAPI |
| `ml/similarity.py` | `ml_service/app/matching.py` and pgvector query | Replace in-memory NumPy comparison with indexed vector search |
| `item_embeddings.npy` | `jewellery_embeddings` table | Store embeddings per image in PostgreSQL |
| `Dataset/` | Versioned dataset storage | Use for evaluation, benchmarking, and future fine-tuning |

### 11.3 Frontend migration

| Current Template | New React Page | Key Change |
|---|---|---|
| `index.html` | `DashboardPage.tsx` | Fetch data through REST APIs |
| `register.html` | `RegisterCustomerPage.tsx` | Client-side validation, webcam component, direct-to-storage upload |
| `register_success.html` | Success state in registration flow | Avoid full-page reload |
| `customers.html` | `PledgeRecordsPage.tsx` | Paginated, searchable data table |
| `results.html` | `MatchResultsPage.tsx` | Async search status and ranked result cards |

## 12. Image Matching Pipeline

### 12.1 Pledge-time flow

1. Staff opens **Register Customer**.
2. Staff enters name, phone number, and Aadhaar number.
3. Staff captures multiple ornament images using webcam or uploads files.
4. React requests presigned URLs and uploads images directly to MinIO/S3.
5. React submits the onboarding payload to Django.
6. Django creates customer, pledge, jewellery-item, and image records in one transaction.
7. Celery dispatches embedding-generation tasks.
8. FastAPI downloads the image from object storage, preprocesses it, and generates a ResNet-50 embedding.
9. Django stores the embedding in pgvector.
10. The pledge becomes searchable in the Vision Match Engine.

### 12.2 Re-pledge identification flow

1. Staff opens **Jewellery Identification**.
2. Staff uploads an image or captures a live photo.
3. React uploads the image and calls the matching API.
4. Django creates a `MatchSearch` record.
5. The ML service generates the query embedding.
6. pgvector performs cosine-distance nearest-neighbor search.
7. Django enriches results with customer, pledge, jewellery, and image data.
8. React displays ranked matches.
9. Staff verifies the result using the displayed photo, customer details, and physical ornament inspection.

### 12.3 Similarity formula

For query embedding \(q\) and stored embedding \(d\):

\[
\text{cosine similarity} = \frac{q \cdot d}{\lVert q \rVert \lVert d \rVert}
\]

pgvector can retrieve nearest neighbors using cosine distance:

```sql
SELECT
  j.id,
  p.pledge_code,
  c.full_name,
  1 - (e.embedding <=> :query_embedding) AS similarity_score
FROM jewellery_embeddings e
JOIN jewellery_images ji ON ji.id = e.jewellery_image_id
JOIN jewellery_items j ON j.id = ji.jewellery_item_id
JOIN pledges p ON p.id = j.pledge_id
JOIN customers c ON c.id = p.customer_id
ORDER BY e.embedding <=> :query_embedding
LIMIT :top_k;
```

## 13. Security Changes From Flask Prototype

The current prototype appears to expose customer KYC data and deletion actions directly from the dashboard. The revised system should introduce stronger controls.

### 13.1 Authentication

Add JWT authentication before production deployment.

- Short-lived access tokens
- Refresh tokens
- Secure HTTP-only refresh-cookie option
- Account lockout after repeated failed attempts
- Session revocation on logout

### 13.2 Authorization

| Role | Dashboard | Register Customer | Delete Pledge | Match Search | Admin |
|---|---|---|---|---|---|
| Branch Staff | View | Create | No | Yes | No |
| Branch Manager | View | Create | Yes | Yes | Limited |
| Auditor | View | No | No | View only | No |
| System Admin | View | Yes | Yes | Yes | Yes |

### 13.3 Data protection

- Mask Aadhaar numbers in list views: `XXXX XXXX 7814`.
- Restrict full Aadhaar visibility to authorized roles.
- Use private image buckets and short-lived presigned URLs.
- Require confirmation before deleting a pledge.
- Prefer soft deletion and archival over hard deletion.
- Record every delete, search, and match-review action in the audit log.
- Validate uploaded file MIME type, extension, size, and checksum.
- Scan uploads for malware in production.

## 14. Revised Docker Compose

```yaml
version: "3.9"

services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  backend:
    build: ./backend
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    env_file: .env
    depends_on:
      - db
      - redis
      - minio
    ports:
      - "8000:8000"

  ml-service:
    build: ./ml_service
    command: uvicorn app.main:app --host 0.0.0.0 --port 8001
    env_file: .env
    depends_on:
      - minio
    ports:
      - "8001:8001"

  celery:
    build: ./backend
    command: celery -A config worker --loglevel=info
    env_file: .env
    depends_on:
      - db
      - redis
      - ml-service

  frontend:
    build: ./frontend
    environment:
      VITE_API_BASE_URL: http://localhost:8000/api/v1
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
  minio_data:
```

## 15. Implementation Milestones

### Phase 1 — Flask-to-Django backend migration

- Create Django project and DRF application.
- Recreate customer, pledge, jewellery-item, and image models.
- Migrate SQLite records to PostgreSQL.
- Implement pledge listing, search, detail, and deletion APIs.
- Add pledge-code generation in the `GS-YYYY-NNNN` format.

**Deliverable:** Django backend reproduces the current Flask customer and pledge functionality.

### Phase 2 — React frontend migration

- Build React application with routing and API client.
- Recreate Dashboard, Register Customer, Pledge Records, Jewellery Identification, and Match Results screens.
- Implement search, pagination, image preview, form validation, and delete confirmation.
- Connect all pages to Django REST APIs.

**Deliverable:** React frontend matches the wireframes and replaces Jinja templates.

### Phase 3 — Storage and asynchronous processing

- Replace `static/uploads/` with MinIO/S3.
- Implement presigned uploads and private image access.
- Add thumbnail generation and checksum validation.
- Configure Celery and Redis.
- Move embedding generation to background tasks.

**Deliverable:** Scalable image-upload and processing pipeline.

### Phase 4 — ML service and pgvector search

- Extract `feature_extraction.py` into the FastAPI service.
- Expose `/embed` and `/match` endpoints.
- Replace `item_embeddings.npy` with pgvector storage.
- Implement cosine top-k retrieval.
- Add model versioning and re-embedding support.

**Deliverable:** Production-ready jewellery identification pipeline.

### Phase 5 — Security, audit, and deployment

- Add JWT authentication and role-based permissions.
- Mask sensitive KYC fields.
- Add audit logging for critical operations.
- Add tests, monitoring, logging, and rate limiting.
- Containerize and deploy all services.

**Deliverable:** Secure, deployable enterprise version of GoldSafe.

## 16. Testing Additions for Wireframe Parity

| Wireframe feature | Test case |
|---|---|
| Total pledges card | Correct count after creating and deleting pledges |
| Search bar | Search by name, phone, Aadhaar, and pledge ID |
| Register Customer | Valid onboarding creates customer, pledge, item, and images |
| Webcam capture | Captured image is uploaded and previewed correctly |
| File upload | JPG, PNG, and WEBP files are accepted; unsupported files rejected |
| Pledge records table | Correct photo, customer, phone, Aadhaar, date, and pledge ID displayed |
| Delete action | Confirmation is required and audit event is recorded |
| Find Similar Items | Query image returns ranked matches above threshold |
| Live camera | Camera stream starts, captures image, and submits correctly |
| Match results | Results show similarity score, stored image, pledge ID, and customer details |

## 17. Deployment Recommendations

- Serve the React build through Nginx or a CDN.
- Run Django with Gunicorn behind Nginx.
- Run FastAPI with Uvicorn workers.
- Use managed PostgreSQL with pgvector in production where available.
- Use private S3 buckets with server-side encryption.
- Store secrets in a secure secret manager.
- Enable centralized logs and error tracking.
- Monitor embedding failures, search latency, upload failures, and Celery queue depth.
- Use rolling or blue-green deployment for zero-downtime releases.
