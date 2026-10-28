import logging

from celery import shared_task
from botocore.exceptions import BotoCoreError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image

from apps.pledges.image_storage import create_thumbnail, read_stored_image, validate_staged_image
from .indexing import index_pledge_image
from .models import JewelleryImage


logger = logging.getLogger(__name__)


@shared_task(ignore_result=True, acks_late=True, reject_on_worker_lost=True)
def process_pledge_image(image_id):
    try:
        image = JewelleryImage.objects.get(pk=image_id)
    except JewelleryImage.DoesNotExist:
        logger.warning("Cannot process missing pledge image %s", image_id)
        return False

    image.embedding_status = JewelleryImage.EmbeddingStatus.PROCESSING
    image.save(update_fields=["embedding_status"])
    try:
        content = read_stored_image(image.object_key)
        actual = validate_staged_image(
            image.object_key,
            claimed_size=image.file_size_bytes,
            claimed_content_type=image.content_type,
            claimed_checksum=image.checksum_sha256,
            content=content,
        )
        thumbnail_key = f"thumbnails/{image.id}.webp"
        if default_storage.exists(thumbnail_key):
            saved_thumbnail = thumbnail_key
        else:
            saved_thumbnail = default_storage.save(thumbnail_key, ContentFile(create_thumbnail(content)))
        image.thumbnail_object_key = saved_thumbnail
        image.save(update_fields=["thumbnail_object_key"])
    except (BotoCoreError, Image.DecompressionBombError, OSError, ValueError) as error:
        logger.exception("Could not validate or thumbnail pledge image %s", image.id)
        image.embedding_status = JewelleryImage.EmbeddingStatus.FAILED
        image.save(update_fields=["embedding_status"])
        return False

    return index_pledge_image(image)
