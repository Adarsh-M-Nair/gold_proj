import os
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = os.environ.get("DATABASE_URL", "")
MODEL_VERSION = os.environ.get("EMBEDDING_MODEL_VERSION", "resnet50-imagenet1k-v2")
EMBEDDING_DIMENSIONS = 2048
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_DATASET_DIR = REPOSITORY_ROOT / "Dataset"
