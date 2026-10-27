from contextlib import asynccontextmanager
from threading import Lock
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile

from .embeddings import ImageValidationError, ResNetEmbedder
from .settings import MAX_UPLOAD_BYTES, MODEL_VERSION
from .storage import EmbeddingStore


store: EmbeddingStore | None = None
embedder: ResNetEmbedder | None = None
embedder_lock = Lock()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global store
    store = EmbeddingStore()
    store.initialize()
    yield


app = FastAPI(title="GoldSafe ML Service", version="1.0.0", lifespan=lifespan)


def get_embedder() -> ResNetEmbedder:
    global embedder
    if embedder is None:
        with embedder_lock:
            if embedder is None:
                embedder = ResNetEmbedder()
    return embedder


def get_store() -> EmbeddingStore:
    if store is None:
        raise RuntimeError("The ML service storage has not been initialized.")
    return store


def read_image(image: UploadFile) -> bytes:
    content = image.file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Choose an image to process.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image files must be 10 MB or smaller.")
    return content


def embed_image(image_bytes: bytes):
    try:
        return get_embedder().embed(image_bytes)
    except ImageValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.post("/embed")
def embed(
    image: Annotated[UploadFile, File()],
    category: Annotated[str | None, Form()] = None,
    item_id: Annotated[str | None, Form()] = None,
) -> dict[str, object]:
    if (category is None) != (item_id is None):
        raise HTTPException(status_code=400, detail="Provide both category and item_id to store an embedding.")
    if category is not None and (not category.strip() or not item_id or not item_id.strip()):
        raise HTTPException(status_code=400, detail="category and item_id cannot be blank.")

    vector = embed_image(read_image(image))
    stored = category is not None and item_id is not None
    if stored:
        get_store().upsert(category.strip(), item_id.strip(), MODEL_VERSION, vector)
    return {
        "category": category.strip() if category else "",
        "item_id": item_id.strip() if item_id else "",
        "model_version": MODEL_VERSION,
        "dimensions": int(vector.shape[0]),
        "embedding": vector.tolist(),
        "stored": stored,
    }


@app.post("/match")
def match(
    image: Annotated[UploadFile, File()],
    top_k: Annotated[int, Query(ge=1, le=50)] = 5,
) -> dict[str, object]:
    vector = embed_image(read_image(image))
    matches = get_store().match(vector, MODEL_VERSION, top_k)
    for rank, result in enumerate(matches, start=1):
        result["rank"] = rank
        result["result_id"] = str(uuid4())
    return {"model_version": MODEL_VERSION, "matches": matches}


@app.post("/pledge-images/embed")
def embed_pledge_image(
    image: Annotated[UploadFile, File()],
    image_id: Annotated[str, Form()],
) -> dict[str, object]:
    image_id = image_id.strip()
    if not image_id:
        raise HTTPException(status_code=400, detail="image_id cannot be blank.")
    vector = embed_image(read_image(image))
    get_store().upsert_pledge_image(image_id, MODEL_VERSION, vector)
    return {"image_id": image_id, "model_version": MODEL_VERSION, "stored": True}


@app.post("/pledge-images/match")
def match_pledge_images(
    image: Annotated[UploadFile, File()],
    top_k: Annotated[int, Query(ge=1, le=200)] = 20,
) -> dict[str, object]:
    vector = embed_image(read_image(image))
    matches = get_store().match_pledge_images(vector, MODEL_VERSION, top_k)
    return {"model_version": MODEL_VERSION, "matches": matches}
