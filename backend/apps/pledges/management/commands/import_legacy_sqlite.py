import json
import mimetypes
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.customers.models import Customer
from apps.jewellery.models import JewelleryImage, JewelleryItem
from apps.pledges.models import Pledge, PledgeCodeSequence


def _photo_paths(stored_value):
    value = (stored_value or "").strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        parsed = None
    if isinstance(parsed, list):
        return [str(path).strip().replace("\\", "/") for path in parsed if str(path).strip()]
    if "," in value:
        return [path.strip().replace("\\", "/") for path in value.split(",") if path.strip()]
    return [value.replace("\\", "/")]


def _created_at(value):
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            parsed = timezone.now()
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_default_timezone())
    return parsed


def _max_sequence(pledge_code, year):
    match = re.fullmatch(rf"GS-{year}-(\d+)", pledge_code or "")
    return int(match.group(1)) if match else 0


class Command(BaseCommand):
    help = "Import legacy customers.db records into Django customer, pledge, item, and image tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=str(settings.REPO_ROOT / "customers.db"),
            help="Path to the legacy SQLite customers.db file.",
        )

    def handle(self, *args, **options):
        source = Path(options["source"]).expanduser().resolve()
        if not source.is_file():
            raise CommandError(f"Legacy database not found: {source}")

        try:
            connection = sqlite3.connect(str(source))
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT pledge_id, name, phone, aadhar, ornament_photo, created_at "
                "FROM customers ORDER BY id"
            ).fetchall()
        except sqlite3.Error as error:
            raise CommandError(f"Could not read legacy customers table: {error}") from error
        finally:
            if "connection" in locals():
                connection.close()

        imported = 0
        skipped = 0
        for row in rows:
            with transaction.atomic():
                if Pledge.objects.filter(pledge_code=row["pledge_id"]).exists():
                    skipped += 1
                    continue

                created_at = _created_at(row["created_at"])
                aadhaar_number = (row["aadhar"] or "").strip()
                aadhaar_digits = re.sub(r"\D", "", aadhaar_number)
                if len(aadhaar_digits) == 12:
                    aadhaar_number = aadhaar_digits
                customer = Customer.objects.create(
                    full_name=(row["name"] or "").strip(),
                    phone_number=(row["phone"] or "").strip(),
                    aadhaar_number=aadhaar_number,
                    created_at=created_at,
                )
                pledge = Pledge.objects.create(
                    pledge_code=row["pledge_id"],
                    customer=customer,
                    pledge_date=created_at.date(),
                    created_at=created_at,
                )
                item = JewelleryItem.objects.create(pledge=pledge, created_at=created_at)
                for index, object_key in enumerate(_photo_paths(row["ornament_photo"])):
                    content_type = mimetypes.guess_type(object_key)[0] or "application/octet-stream"
                    JewelleryImage.objects.create(
                        jewellery_item=item,
                        pledge=pledge,
                        object_key=object_key,
                        original_filename=Path(object_key).name[:255],
                        content_type=content_type,
                        image_type=JewelleryImage.ImageType.FRONT if index == 0 else JewelleryImage.ImageType.OTHER,
                        created_at=created_at,
                    )

                sequence_value = _max_sequence(pledge.pledge_code, created_at.year)
                if sequence_value:
                    counter, _ = PledgeCodeSequence.objects.get_or_create(year=created_at.year)
                    if sequence_value > counter.last_sequence:
                        counter.last_sequence = sequence_value
                        counter.save(update_fields=["last_sequence"])
                imported += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {imported} records; skipped {skipped} existing pledges."))