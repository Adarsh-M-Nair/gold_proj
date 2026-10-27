import uuid

from django.db import models
from django.utils import timezone


class JewelleryItem(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        RETURNED = "RETURNED", "Returned"
        FLAGGED = "FLAGGED", "Flagged"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pledge = models.ForeignKey("pledges.Pledge", on_delete=models.CASCADE, related_name="items")
    category = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    weight_grams = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    purity = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at", "id"]


class JewelleryImage(models.Model):
    class CaptureSource(models.TextChoices):
        WEBCAM = "WEBCAM", "Webcam"
        UPLOAD = "UPLOAD", "Upload"

    class ImageType(models.TextChoices):
        FRONT = "FRONT", "Front"
        BACK = "BACK", "Back"
        SIDE = "SIDE", "Side"
        CLOSEUP = "CLOSEUP", "Close-up"
        OTHER = "OTHER", "Other"

    class EmbeddingStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    jewellery_item = models.ForeignKey(JewelleryItem, on_delete=models.CASCADE, related_name="images")
    pledge = models.ForeignKey("pledges.Pledge", on_delete=models.CASCADE, related_name="images")
    object_key = models.CharField(max_length=1024)
    thumbnail_object_key = models.CharField(max_length=1024, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, default="application/octet-stream")
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    capture_source = models.CharField(max_length=10, choices=CaptureSource.choices, default=CaptureSource.UPLOAD)
    image_type = models.CharField(max_length=10, choices=ImageType.choices, default=ImageType.OTHER)
    embedding_status = models.CharField(max_length=12, choices=EmbeddingStatus.choices, default=EmbeddingStatus.PENDING)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at", "id"]