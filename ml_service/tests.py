import asyncio
from io import BytesIO
import unittest
from unittest.mock import patch

import httpx
import numpy as np
from PIL import Image

from ml_service.app import main
from ml_service.app.embeddings import ImageValidationError, ResNetEmbedder


class FakeStore:
    def __init__(self) -> None:
        self.saved: list[tuple[str, str, str, np.ndarray]] = []
        self.top_k: int | None = None

    def upsert(self, category: str, item_id: str, model_version: str, embedding: np.ndarray) -> None:
        self.saved.append((category, item_id, model_version, embedding))

    def match(self, _embedding: np.ndarray, _model_version: str, top_k: int) -> list[dict[str, str | float]]:
        self.top_k = top_k
        return [{"category": "Bangle", "item_id": "Bangle_001", "similarity_score": 0.9}]

    def upsert_pledge_image(self, image_id: str, model_version: str, embedding: np.ndarray) -> None:
        self.saved.append(("PLEDGE", image_id, model_version, embedding))

    def match_pledge_images(
        self, _embedding: np.ndarray, _model_version: str, top_k: int
    ) -> list[dict[str, str | float]]:
        self.top_k = top_k
        return [{"image_id": "image-1", "similarity_score": 0.8}]


class FakeEmbedder:
    def embed(self, _image_bytes: bytes) -> np.ndarray:
        return np.ones(2048, dtype=np.float32)


def image_bytes() -> bytes:
    image = BytesIO()
    Image.new("RGB", (4, 4), color="gold").save(image, format="PNG")
    return image.getvalue()


class MLServiceTests(unittest.TestCase):
    async def post(
        self,
        path: str,
        *,
        files: dict[str, tuple[str, bytes, str]],
        data: dict[str, str] | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app),
            base_url="http://testserver",
        ) as client:
            return await client.post(path, files=files, data=data)

    def test_embed_stores_versioned_vector_when_item_is_identified(self) -> None:
        store = FakeStore()
        with (
            patch.object(main, "store", store),
            patch("ml_service.app.main.get_embedder", return_value=FakeEmbedder()),
        ):
            response = asyncio.run(self.post(
                "/embed",
                files={"image": ("item.png", image_bytes(), "image/png")},
                data={"category": "Bangle", "item_id": "Bangle_001"},
            ))

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["category"], "Bangle")
        self.assertEqual(result["item_id"], "Bangle_001")
        self.assertEqual(result["model_version"], main.MODEL_VERSION)
        self.assertEqual(result["dimensions"], 2048)
        self.assertTrue(result["stored"])
        self.assertEqual(len(store.saved), 1)
        self.assertEqual(store.saved[0][:3], ("Bangle", "Bangle_001", main.MODEL_VERSION))
        self.assertEqual(len(result["embedding"]), 2048)

    def test_match_returns_ranked_cosine_results_and_honors_top_k(self) -> None:
        store = FakeStore()
        with (
            patch.object(main, "store", store),
            patch("ml_service.app.main.get_embedder", return_value=FakeEmbedder()),
        ):
            response = asyncio.run(self.post(
                "/match?top_k=3",
                files={"image": ("query.png", image_bytes(), "image/png")},
            ))

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["model_version"], main.MODEL_VERSION)
        self.assertEqual(result["matches"][0]["rank"], 1)
        self.assertEqual(result["matches"][0]["category"], "Bangle")
        self.assertEqual(result["matches"][0]["similarity_score"], 0.9)
        self.assertTrue(result["matches"][0]["result_id"])
        self.assertEqual(store.top_k, 3)

    def test_pledge_image_embed_stores_vector_by_image_id(self) -> None:
        store = FakeStore()
        with (
            patch.object(main, "store", store),
            patch("ml_service.app.main.get_embedder", return_value=FakeEmbedder()),
        ):
            response = asyncio.run(self.post(
                "/pledge-images/embed",
                files={"image": ("pledge.png", image_bytes(), "image/png")},
                data={"image_id": " image-1 "},
            ))
            blank = asyncio.run(self.post(
                "/pledge-images/embed",
                files={"image": ("pledge.png", image_bytes(), "image/png")},
                data={"image_id": "  "},
            ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"image_id": "image-1", "model_version": main.MODEL_VERSION, "stored": True})
        self.assertEqual(store.saved[0][:3], ("PLEDGE", "image-1", main.MODEL_VERSION))
        self.assertEqual(blank.status_code, 400)
        self.assertEqual(len(store.saved), 1)

    def test_pledge_image_match_returns_scored_image_ids(self) -> None:
        store = FakeStore()
        with (
            patch.object(main, "store", store),
            patch("ml_service.app.main.get_embedder", return_value=FakeEmbedder()),
        ):
            response = asyncio.run(self.post(
                "/pledge-images/match?top_k=40",
                files={"image": ("query.png", image_bytes(), "image/png")},
            ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["matches"], [{"image_id": "image-1", "similarity_score": 0.8}])
        self.assertEqual(store.top_k, 40)

    def test_embedder_rejects_non_image_bytes(self) -> None:
        embedder = ResNetEmbedder.__new__(ResNetEmbedder)
        with self.assertRaises(ImageValidationError):
            embedder.embed(b"not an image")
