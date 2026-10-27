import uuid

from django.db import models
from django.utils import timezone


class PledgeCodeSequence(models.Model):
    year = models.PositiveSmallIntegerField(primary_key=True)
    last_sequence = models.PositiveIntegerField(default=0)


class Pledge(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"
        RE_PLEDGED = "RE_PLEDGED", "Re-pledged"
        DELETED = "DELETED", "Deleted"
        FLAGGED = "FLAGGED", "Flagged"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pledge_code = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="pledges",
    )
    branch_id = models.UUIDField(null=True, blank=True)
    pledge_date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    total_weight_grams = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    estimated_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return self.pledge_code