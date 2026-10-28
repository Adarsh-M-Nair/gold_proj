import hashlib
import re
import uuid
from io import BytesIO
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError
from django.conf import settings
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.urls import reverse
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
IMAGE_FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}
UPLOAD_KEY_PATTERN = re.compile(r"^uploads/[0-9a-f]{32}\.(?:jpg|png|webp)$")
PRIVATE_IMAGE_SALT = "goldsafe-private-image"


class InvalidImageUpload(ValueError):
    pass


def object_storage_enabled():
    return bool(settings.OBJECT_STORAGE_BUCKET)


def storage_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.OBJECT_STORAGE_ENDPOINT_URL or None,
        region_name=settings.OBJECT_STORAGE_REGION,
        aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY or None,
        aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_KEY or None,
        config=Config(s3={"addressing_style": settings.OBJECT_STORAGE_ADDRESSING_STYLE}),
    )


def validate_upload_metadata(data):
    filename_value = data.get("filename", "")
    content_type = data.get("content_type", "")
    if not isinstance(filename_value, str) or not isinstance(content_type, str):
        raise InvalidImageUpload("Provide a valid image filename and content type.")
    filename = Path(filename_value).name
    file_size_value = data.get("file_size_bytes")
    if isinstance(file_size_value, bool):
        raise InvalidImageUpload("Provide the image's file size.")
    try:
        file_size = int(file_size_value)
    except (TypeError, ValueError):
        raise InvalidImageUpload("Provide the image's file size.")
    if isinstance(file_size_value, float) and file_size_value != file_size:
        raise InvalidImageUpload("Provide the image's file size as a whole number.")
    if filename in ("", ".", "..") or len(filename) > 255:
        raise InvalidImageUpload("Provide a valid image filename.")
    if content_type not in {details[1] for details in IMAGE_FORMATS.values()}:
        raise InvalidImageUpload("Only JPG, PNG, and WEBP images are supported.")
    if not 0 < file_size <= MAX_UPLOAD_BYTES:
        raise InvalidImageUpload("Image files must be between 1 byte and 10 MB.")
    return filename, content_type, file_size


def create_upload_request(request, filename, content_type, file_size):
    extension = next(ext for ext, mime in IMAGE_FORMATS.values() if mime == content_type)
    object_key = f"uploads/{uuid.uuid4().hex}.{extension}"
    if object_storage_enabled():
        presigned = storage_client().generate_presigned_post(
            Bucket=settings.OBJECT_STORAGE_BUCKET,
            Key=object_key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"key": object_key},
                {"Content-Type": content_type},
                ["content-length-range", file_size, file_size + 65536],
            ],
            ExpiresIn=300,
        )
        return {
            "method": "POST",
            "upload_url": presigned["url"],
            "fields": presigned["fields"],
            "object_key": object_key,
            "original_filename": filename,
            "content_type": content_type,
            "file_size_bytes": file_size,
        }

    return {
        "method": "LOCAL",
        "upload_url": request.build_absolute_uri(reverse("image-upload")),
        "object_key": "",
        "fields": {},
        "original_filename": filename,
        "content_type": content_type,
        "file_size_bytes": file_size,
    }


def read_stored_image(object_key):
    with default_storage.open(object_key, "rb") as stored:
        return stored.read()


def inspect_image_content(content):
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise InvalidImageUpload("Image files must be between 1 byte and 10 MB.")
    try:
        with Image.open(BytesIO(content)) as image:
            image_format = image.format
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise InvalidImageUpload("The uploaded file is not a valid image.") from error
    format_details = IMAGE_FORMATS.get(image_format or "")
    if format_details is None:
        raise InvalidImageUpload("Only JPG, PNG, and WEBP images are supported.")
    extension, content_type = format_details
    return {
        "file_size_bytes": len(content),
        "content_type": content_type,
        "checksum_sha256": hashlib.sha256(content).hexdigest(),
        "extension": extension,
    }


def validate_staged_image(
    object_key,
    claimed_size=None,
    claimed_content_type=None,
    claimed_checksum=None,
    content=None,
):
    if not UPLOAD_KEY_PATTERN.fullmatch(object_key):
        raise InvalidImageUpload("The image must reference a valid uploaded object.")
    if content is None:
        try:
            content = read_stored_image(object_key)
        except (BotoCoreError, FileNotFoundError, OSError, ValueError) as error:
            raise InvalidImageUpload("The uploaded image could not be found.") from error
    details = inspect_image_content(content)
    if claimed_size not in (None, 0, details["file_size_bytes"]):
        raise InvalidImageUpload("The uploaded image size does not match its metadata.")
    if claimed_content_type not in (None, "", details["content_type"]):
        raise InvalidImageUpload("The uploaded image type does not match its content.")
    if claimed_checksum and claimed_checksum.lower() != details["checksum_sha256"]:
        raise InvalidImageUpload("The uploaded image checksum does not match.")
    return details


def save_uploaded_image(content):
    details = inspect_image_content(content)
    object_key = f"uploads/{uuid.uuid4().hex}.{details['extension']}"
    saved_key = default_storage.save(object_key, ContentFile(content))
    return saved_key, details


def private_image_url(request, object_key):
    if object_key.startswith("static/uploads/"):
        token = signing.dumps(object_key, salt=PRIVATE_IMAGE_SALT)
        return request.build_absolute_uri(reverse("pledge-image-access", args=[token]))
    if object_storage_enabled():
        return default_storage.url(
            object_key,
            parameters={"ResponseCacheControl": "private, no-store"},
        )
    token = signing.dumps(object_key, salt=PRIVATE_IMAGE_SALT)
    return request.build_absolute_uri(reverse("pledge-image-access", args=[token]))


def create_thumbnail(content):
    with Image.open(BytesIO(content)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((512, 512), Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, format="WEBP", quality=82, method=6)
    return output.getvalue()
