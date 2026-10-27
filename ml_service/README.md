# GoldSafe ML service

The FastAPI service extracts normalized 2,048-dimensional ResNet-50 features and stores searchable reference-item embeddings as pgvector `halfvec` values with a cosine HNSW index. Half-precision indexing supports the model's 2,048 dimensions. It runs independently of the Django API and does not require Phase 3 storage or Celery.

## Configuration and start

Install the root `requirements.txt`, make sure PostgreSQL has the pgvector extension available, and set `DATABASE_URL` to the same PostgreSQL database used by Django. The service creates its `jewellery_embeddings` table and cosine HNSW index on startup. Set `EMBEDDING_MODEL_VERSION` to version a changed model or preprocessing pipeline; the default is `resnet50-imagenet1k-v2`.

```powershell
$env:DATABASE_URL = "postgresql://user:password@localhost:5432/goldsafe"
uvicorn ml_service.app.main:app --host 127.0.0.1 --port 8001
```

The first embedding request loads the pretrained ResNet-50 ImageNet V2 weights through torchvision. The configured database must permit creating the `vector` extension (or have it pre-installed by an administrator).

## Endpoints

- `GET /health` reports service/model readiness.
- `POST /embed` accepts multipart `image` and returns the normalized vector; optionally provide both `category` and `item_id` to upsert it. Uploads are limited to 10 MB.
- `POST /match?top_k=5` accepts multipart `image` and returns the nearest reference catalogue items for the active model version, ranked by cosine similarity.
- `POST /pledge-images/embed` accepts multipart `image` and `image_id` (a Django `JewelleryImage` id) and upserts that pledge image's embedding into `pledge_image_embeddings`.
- `POST /pledge-images/match?top_k=20` accepts multipart `image` and returns the nearest pledge images as `image_id` and `similarity_score` pairs (`top_k` up to 200).

The Django endpoint `POST /api/v1/matching/search/` forwards the frontend's multipart image upload to `/pledge-images/match` and turns the matched image ids into pledge records. Django calls `/pledge-images/embed` for every image when a pledge is registered. Set Django's `ML_SERVICE_URL` if the ML service is not at `http://127.0.0.1:8001`.

## Index and re-embed the dataset

Run this command after setting `DATABASE_URL`. Every dataset item is indexed from the normalized mean of its valid JPG, PNG, and WEBP image embeddings. Running it again updates the current model version; changing `EMBEDDING_MODEL_VERSION` retains old rows and indexes replacements separately.

```powershell
python -m ml_service.app.reembed
python -m ml_service.app.reembed --dataset "C:\path\to\Dataset"
```

Run the ML API contract tests with `python -m unittest ml_service.tests`.
