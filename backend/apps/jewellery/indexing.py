import logging
from pathlib import Path

import httpx
from botocore.exceptions import BotoCoreError
from django.conf import settings
from django.core.files.storage import default_storage

from .models import JewelleryImage


logger = logging.getLogger(__name__)
LEGACY_UPLOAD_PREFIX = "static/uploads/"


class PledgeImageUnavailable(Exception):
    pass


def read_pledge_image(image):
    object_key = image.object_key.lstrip("/")
    if object_key.startswith("media/"):
        object_key = object_key[len("media/"):]
    if object_key.startswith(LEGACY_UPLOAD_PREFIX):
        # Images imported from the legacy Flask app live under the repository's static/uploads folder.
        legacy_root = (Path(settings.REPO_ROOT) / LEGACY_UPLOAD_PREFIX).resolve()
        path = (Path(settings.REPO_ROOT) / object_key).resolve()
        if legacy_root not in path.parents or not path.is_file():
            raise PledgeImageUnavailable(f"Image file not found: {image.object_key}")
        return path.read_bytes()
    try:
        with default_storage.open(object_key, "rb") as stored:
            return stored.read()
    except (BotoCoreError, FileNotFoundError, OSError, ValueError) as error:
        raise PledgeImageUnavailable(f"Image file not found: {image.object_key}") from error


def index_pledge_image(image):
    """Embed one pledge image in the ML service and record the outcome on the image."""
    try:
        content = read_pledge_image(image)
        response = httpx.post(
            f"{settings.ML_SERVICE_URL}/pledge-images/embed",
            data={"image_id": str(image.id)},
            files={"image": (Path(image.object_key).name, content, image.content_type or "application/octet-stream")},
            timeout=60.0,
        )
        response.raise_for_status()
    except PledgeImageUnavailable as error:
        logger.warning("Skipped pledge image %s: %s", image.id, error)
        status = JewelleryImage.EmbeddingStatus.FAILED
    except httpx.HTTPError:
        logger.exception("Could not index pledge image %s in the ML service", image.id)
        status = JewelleryImage.EmbeddingStatus.FAILED
    else:
        status = JewelleryImage.EmbeddingStatus.COMPLETED

    image.embedding_status = status
    image.save(update_fields=["embedding_status"])
    return status == JewelleryImage.EmbeddingStatus.COMPLETED


def index_pledge_images(images):
    indexed = failed = 0
    for image in images:
        if index_pledge_image(image):
            indexed += 1
        else:
            failed += 1
    return indexed, failed
