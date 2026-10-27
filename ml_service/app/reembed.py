import argparse
import sys
from pathlib import Path

import numpy as np

from .embeddings import ImageValidationError, ResNetEmbedder
from .settings import DEFAULT_DATASET_DIR, MODEL_VERSION
from .storage import EmbeddingStore


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def reembed_dataset(dataset_dir: Path) -> tuple[int, list[str]]:
    store = EmbeddingStore()
    store.initialize()
    embedder = ResNetEmbedder()
    indexed = 0
    failed_images: list[str] = []

    for category_dir in sorted(path for path in dataset_dir.iterdir() if path.is_dir()):
        for item_dir in sorted(path for path in category_dir.iterdir() if path.is_dir()):
            vectors = []
            for image_path in sorted(
                path for path in item_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
            ):
                try:
                    vectors.append(embedder.embed(image_path.read_bytes()))
                except ImageValidationError:
                    failed_images.append(str(image_path))
                    print(f"Skipped invalid image: {image_path}", file=sys.stderr)

            if not vectors:
                continue
            averaged = np.mean(vectors, axis=0, dtype=np.float32)
            norm = np.linalg.norm(averaged)
            if norm:
                averaged /= norm
            store.upsert(category_dir.name, item_dir.name, MODEL_VERSION, averaged)
            indexed += 1

    return indexed, failed_images


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-embed the jewellery dataset into pgvector.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_DIR)
    args = parser.parse_args()
    if not args.dataset.is_dir():
        parser.error(f"Dataset directory does not exist: {args.dataset}")

    indexed, failed_images = reembed_dataset(args.dataset)
    print(f"Indexed {indexed} items using model {MODEL_VERSION}.")
    if failed_images:
        print(f"Skipped {len(failed_images)} invalid image(s); inspect the messages above.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
