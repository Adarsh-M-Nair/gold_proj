import json
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.customers.models import Customer
from apps.jewellery.models import JewelleryImage, JewelleryItem
from apps.pledges.models import Pledge
from apps.pledges.services import generate_pledge_code


class PledgeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(
            full_name="Test Customer",
            phone_number="9876543210",
            aadhaar_number="123456789012",
        )
        self.pledge = Pledge.objects.create(
            pledge_code="GS-2026-0001",
            customer=self.customer,
            pledge_date=date(2026, 10, 1),
        )

    def test_list_search_masks_aadhaar_and_includes_primary_photo(self):
        item = JewelleryItem.objects.create(pledge=self.pledge, category="RING")
        JewelleryImage.objects.create(
            jewellery_item=item,
            pledge=self.pledge,
            object_key="pledges/ring.jpg",
            thumbnail_object_key="pledges/ring-thumb.jpg",
        )

        response = self.client.get(reverse("pledge-list"), {"search": "9876"})

        self.assertEqual(response.status_code, 200)
        record = response.data["results"][0]
        self.assertEqual(record["pledge_id"], "GS-2026-0001")
        self.assertEqual(record["customer"]["masked_aadhaar"], "XXXX XXXX 9012")
        self.assertNotIn("aadhaar_number", record["customer"])
        self.assertEqual(record["primary_photo"], "pledges/ring-thumb.jpg")

        aadhaar_response = self.client.get(reverse("pledge-list"), {"search": "123456789012"})
        self.assertEqual(aadhaar_response.data["count"], 1)

    def test_detail_and_soft_delete(self):
        detail = self.client.get(reverse("pledge-detail", args=[self.pledge.id]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["pledge_code"], "GS-2026-0001")

        deleted = self.client.delete(reverse("pledge-detail", args=[self.pledge.id]))
        self.assertEqual(deleted.status_code, 204)
        self.pledge.refresh_from_db()
        self.assertEqual(self.pledge.status, Pledge.Status.DELETED)
        self.assertEqual(self.client.get(reverse("pledge-list")).data["count"], 0)

    def test_onboarding_creates_related_records_atomically(self):
        response = self.client.post(
            reverse("customer-onboarding"),
            {
                "customer": {
                    "full_name": "New Customer",
                    "phone_number": "9876543211",
                    "aadhaar_number": "1234 5678 9013",
                },
                "pledge": {"pledge_date": "2026-10-27"},
                "jewellery_item": {"category": "BANGLE", "purity": "22K"},
                "images": [
                    {"object_key": "uploads/front.webp", "image_type": "FRONT"},
                    {"object_key": "uploads/side.webp", "image_type": "SIDE"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["pledge_code"], "GS-2026-0002")
        self.assertEqual(Pledge.objects.count(), 2)
        self.assertEqual(JewelleryItem.objects.count(), 1)
        self.assertEqual(JewelleryImage.objects.count(), 2)
        self.assertEqual(response.data["customer"]["masked_aadhaar"], "XXXX XXXX 9013")

    def test_pledge_code_generation_tracks_existing_codes(self):
        self.assertEqual(generate_pledge_code(2026), "GS-2026-0002")


class LegacyImportTests(TestCase):
    def test_import_splits_legacy_photo_list_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "customers.db"
            connection = sqlite3.connect(source)
            connection.execute(
                "CREATE TABLE customers (id INTEGER PRIMARY KEY, pledge_id TEXT, name TEXT, "
                "phone TEXT, aadhar TEXT, ornament_photo TEXT, created_at TIMESTAMP)"
            )
            connection.execute(
                "INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?)",
                (17, "GS-2026-0042", "Imported Customer", "9876543212", "1234 5678 9014",
                 json.dumps(["uploads/front.jpg", "uploads/side.jpg"]), "2026-10-20 12:00:00"),
            )
            connection.commit()
            connection.close()

            call_command("import_legacy_sqlite", source=str(source), verbosity=0)
            call_command("import_legacy_sqlite", source=str(source), verbosity=0)

        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Customer.objects.get().aadhaar_number, "123456789014")
        self.assertEqual(Pledge.objects.get().pledge_code, "GS-2026-0042")
        self.assertEqual(JewelleryImage.objects.count(), 2)
        response = APIClient().get(reverse("pledge-list"), {"search": "123456789014"})
        self.assertEqual(response.data["count"], 1)