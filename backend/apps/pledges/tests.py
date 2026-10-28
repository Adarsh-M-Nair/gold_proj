import json
import hashlib
import sqlite3
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import httpx
from kombu.exceptions import OperationalError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from PIL import Image
from io import BytesIO, StringIO

from apps.customers.models import Customer
from apps.jewellery.indexing import PledgeImageUnavailable, read_pledge_image
from apps.jewellery.models import JewelleryImage, JewelleryItem
from apps.jewellery.tasks import process_pledge_image
from apps.pledges.serializers import enqueue_image_processing
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
        self.assertIn("/api/v1/images/access/", record["primary_photo"])
        self.assertNotIn("pledges/ring-thumb.jpg", record["primary_photo"])

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

    @patch("apps.pledges.serializers.process_pledge_image.delay")
    def test_onboarding_creates_related_records_and_queues_processing(self, enqueue):
        output = BytesIO()
        Image.new("RGB", (4, 4), color="gold").save(output, format="WEBP")
        image_bytes = output.getvalue()
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            (Path(media_root) / "uploads").mkdir()
            (Path(media_root) / "uploads" / "11111111111111111111111111111111.webp").write_bytes(image_bytes)
            (Path(media_root) / "uploads" / "22222222222222222222222222222222.webp").write_bytes(image_bytes)
            with self.captureOnCommitCallbacks(execute=True):
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
                            {"object_key": "uploads/11111111111111111111111111111111.webp", "image_type": "FRONT"},
                            {"object_key": "uploads/22222222222222222222222222222222.webp", "image_type": "SIDE"},
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

        self.assertEqual(enqueue.call_count, 2)
        self.assertEqual(
            {call.args[0] for call in enqueue.call_args_list},
            {str(image.id) for image in JewelleryImage.objects.filter(pledge_id=response.data["id"])},
        )
        statuses = {
            image["image_url"]: image["embedding_status"] for image in response.data["items"][0]["images"]
        }
        self.assertEqual(set(statuses.values()), {"PENDING"})
        self.assertNotIn("object_key", response.data["items"][0]["images"][0])

    def test_onboarding_rejects_checksum_mismatch(self):
        output = BytesIO()
        Image.new("RGB", (4, 4), color="gold").save(output, format="PNG")
        image_bytes = output.getvalue()
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            (Path(media_root) / "uploads").mkdir()
            (Path(media_root) / "uploads" / "11111111111111111111111111111111.png").write_bytes(image_bytes)
            response = self.client.post(
                reverse("customer-onboarding"),
                {
                    "customer": {
                        "full_name": "New Customer",
                        "phone_number": "9876543211",
                        "aadhaar_number": "1234 5678 9013",
                    },
                    "images": [{
                        "object_key": "uploads/11111111111111111111111111111111.png",
                        "checksum_sha256": hashlib.sha256(b"not the image").hexdigest(),
                    }],
                },
                format="json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Pledge.objects.count(), 1)

    def test_local_upload_fallback_uses_short_lived_private_url(self):
        output = BytesIO()
        Image.new("RGB", (4, 4), color="gold").save(output, format="PNG")
        image_bytes = output.getvalue()
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            presign = self.client.post(
                reverse("image-upload-presign"),
                {
                    "filename": "ornament.png",
                    "content_type": "image/png",
                    "file_size_bytes": len(image_bytes),
                },
                format="json",
            )
            self.assertEqual(presign.status_code, 200)
            self.assertEqual(presign.data["method"], "LOCAL")
            uploaded = self.client.post(
                reverse("image-upload"),
                {"image": SimpleUploadedFile("ornament.png", image_bytes, content_type="image/png")},
                format="multipart",
            )

            self.assertEqual(uploaded.status_code, 201)
            self.assertEqual(uploaded.data["checksum_sha256"], hashlib.sha256(image_bytes).hexdigest())
            private = self.client.get(uploaded.data["url"])
            public = self.client.get(f"/media/{uploaded.data['object_key']}")

        self.assertEqual(private.status_code, 200)
        self.assertEqual(private.content, image_bytes)
        self.assertEqual(private["Cache-Control"], "private, no-store")
        self.assertEqual(public.status_code, 404)

    @patch("apps.pledges.image_storage.storage_client")
    def test_s3_presign_returns_a_signed_post_request(self, storage_client):
        storage_client.return_value.generate_presigned_post.return_value = {
            "url": "https://storage.example/upload",
            "fields": {"key": "uploads/key.webp", "policy": "signed-policy"},
        }
        with override_settings(
            OBJECT_STORAGE_BUCKET="goldsafe-private",
            OBJECT_STORAGE_ENDPOINT_URL="http://127.0.0.1:9000",
            OBJECT_STORAGE_REGION="us-east-1",
        ):
            response = self.client.post(
                reverse("image-upload-presign"),
                {
                    "filename": "ornament.webp",
                    "content_type": "image/webp",
                    "file_size_bytes": 2048,
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["method"], "POST")
        self.assertEqual(response.data["upload_url"], "https://storage.example/upload")
        self.assertRegex(response.data["object_key"], r"^uploads/[0-9a-f]{32}\.webp$")
        self.assertEqual(response.data["fields"]["policy"], "signed-policy")
        storage_client.return_value.generate_presigned_post.assert_called_once()
        call = storage_client.return_value.generate_presigned_post.call_args.kwargs
        self.assertEqual(call["Bucket"], "goldsafe-private")
        self.assertIn(["content-length-range", 2048, 2048 + 65536], call["Conditions"])

    @patch("apps.jewellery.indexing.httpx.post")
    def test_worker_validates_checksum_generates_thumbnail_and_embeds(self, post):
        post.return_value = httpx.Response(200, json={"stored": True}, request=httpx.Request("POST", "http://ml"))
        output = BytesIO()
        Image.new("RGB", (32, 24), color="gold").save(output, format="PNG")
        image_bytes = output.getvalue()
        item = JewelleryItem.objects.create(pledge=self.pledge)

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            (Path(media_root) / "uploads").mkdir()
            key = "uploads/11111111111111111111111111111111.png"
            (Path(media_root) / key).write_bytes(image_bytes)
            image = JewelleryImage.objects.create(
                jewellery_item=item,
                pledge=self.pledge,
                object_key=key,
                content_type="image/png",
                file_size_bytes=len(image_bytes),
                checksum_sha256=hashlib.sha256(image_bytes).hexdigest(),
            )

            self.assertTrue(process_pledge_image.run(str(image.id)))
            image.refresh_from_db()
            self.assertEqual(image.embedding_status, JewelleryImage.EmbeddingStatus.COMPLETED)
            self.assertEqual(image.thumbnail_object_key, f"thumbnails/{image.id}.webp")
            with default_storage.open(image.thumbnail_object_key, "rb") as thumbnail:
                with Image.open(thumbnail) as thumbnail_image:
                    self.assertEqual(thumbnail_image.format, "WEBP")

    @patch("apps.pledges.serializers.process_pledge_image.delay", side_effect=OperationalError("Redis unavailable"))
    def test_registration_survives_queue_unavailability(self, _enqueue):
        item = JewelleryItem.objects.create(pledge=self.pledge)
        image = JewelleryImage.objects.create(
            jewellery_item=item,
            pledge=self.pledge,
            object_key="uploads/11111111111111111111111111111111.png",
        )

        enqueue_image_processing(image.id)

        image.refresh_from_db()
        self.assertEqual(image.embedding_status, JewelleryImage.EmbeddingStatus.FAILED)
        self.assertTrue(process_pledge_image.ignore_result)

    @patch("apps.jewellery.indexing.httpx.post")
    def test_index_command_embeds_pending_and_failed_images_of_live_pledges(self, post):
        post.return_value = httpx.Response(200, json={"stored": True}, request=httpx.Request("POST", "http://ml"))
        item = JewelleryItem.objects.create(pledge=self.pledge)
        pending = JewelleryImage.objects.create(jewellery_item=item, pledge=self.pledge, object_key="uploads/a.png")
        failed = JewelleryImage.objects.create(
            jewellery_item=item, pledge=self.pledge, object_key="uploads/b.png",
            embedding_status=JewelleryImage.EmbeddingStatus.FAILED,
        )
        done = JewelleryImage.objects.create(
            jewellery_item=item, pledge=self.pledge, object_key="uploads/c.png",
            embedding_status=JewelleryImage.EmbeddingStatus.COMPLETED,
        )
        deleted_pledge = Pledge.objects.create(
            pledge_code="GS-2026-0003", customer=self.customer, status=Pledge.Status.DELETED
        )
        deleted_item = JewelleryItem.objects.create(pledge=deleted_pledge)
        JewelleryImage.objects.create(jewellery_item=deleted_item, pledge=deleted_pledge, object_key="uploads/d.png")

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            (Path(media_root) / "uploads").mkdir()
            for name in ["a.png", "b.png", "c.png", "d.png"]:
                (Path(media_root) / "uploads" / name).write_bytes(b"image")
            call_command("index_pledge_images", stdout=StringIO(), stderr=StringIO())
            self.assertEqual(
                [call.kwargs["data"]["image_id"] for call in post.call_args_list], [str(pending.id), str(failed.id)]
            )

            post.reset_mock()
            call_command("index_pledge_images", "--all", stdout=StringIO(), stderr=StringIO())
            self.assertEqual(post.call_count, 3)

        for image in (pending, failed, done):
            image.refresh_from_db()
            self.assertEqual(image.embedding_status, JewelleryImage.EmbeddingStatus.COMPLETED)

    @patch("apps.jewellery.indexing.httpx.post", side_effect=httpx.ConnectError("offline"))
    def test_index_marks_images_failed_when_ml_service_is_unavailable(self, _post):
        item = JewelleryItem.objects.create(pledge=self.pledge)
        image = JewelleryImage.objects.create(jewellery_item=item, pledge=self.pledge, object_key="uploads/a.png")
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            (Path(media_root) / "uploads").mkdir()
            (Path(media_root) / "uploads" / "a.png").write_bytes(b"image")
            call_command("index_pledge_images", stdout=StringIO(), stderr=StringIO())

        image.refresh_from_db()
        self.assertEqual(image.embedding_status, JewelleryImage.EmbeddingStatus.FAILED)

    def test_index_reads_legacy_static_upload_paths_inside_repository_only(self):
        item = JewelleryItem.objects.create(pledge=self.pledge)
        legacy = JewelleryImage(jewellery_item=item, pledge=self.pledge, object_key="static/uploads/old.jpg")
        escape = JewelleryImage(jewellery_item=item, pledge=self.pledge, object_key="static/uploads/../secret.txt")
        with tempfile.TemporaryDirectory() as repo_root, override_settings(REPO_ROOT=Path(repo_root)):
            (Path(repo_root) / "static" / "uploads").mkdir(parents=True)
            (Path(repo_root) / "static" / "uploads" / "old.jpg").write_bytes(b"legacy")
            (Path(repo_root) / "static" / "secret.txt").write_bytes(b"secret")
            self.assertEqual(read_pledge_image(legacy), b"legacy")
            with self.assertRaises(PledgeImageUnavailable):
                read_pledge_image(escape)

    def test_pledge_code_generation_tracks_existing_codes(self):
        self.assertEqual(generate_pledge_code(2026), "GS-2026-0002")

    def test_image_upload_stores_verified_image_and_returns_metadata(self):
        output = BytesIO()
        Image.new("RGB", (4, 4), color="gold").save(output, format="PNG")
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("image-upload"),
                    {"image": SimpleUploadedFile("ornament.png", output.getvalue(), content_type="image/png")},
                    format="multipart",
                )

                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.data["content_type"], "image/png")
                self.assertEqual(response.data["original_filename"], "ornament.png")
                self.assertTrue((Path(media_root) / response.data["object_key"]).is_file())

    def test_image_upload_rejects_non_image_files(self):
        response = self.client.post(
            reverse("image-upload"),
            {"image": SimpleUploadedFile("not-an-image.jpg", b"not an image", content_type="image/jpeg")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.data)

    @patch("apps.pledges.views.httpx.post")
    def test_matching_search_returns_matching_pledge_records(self, post):
        item = JewelleryItem.objects.create(pledge=self.pledge, category="RING", description="Floral ring")
        front = JewelleryImage.objects.create(jewellery_item=item, pledge=self.pledge, object_key="uploads/front.jpg")
        side = JewelleryImage.objects.create(jewellery_item=item, pledge=self.pledge, object_key="uploads/side.jpg")
        other_customer = Customer.objects.create(
            full_name="Other Customer", phone_number="9876500000", aadhaar_number="999988887777"
        )
        other_pledge = Pledge.objects.create(pledge_code="GS-2026-0003", customer=other_customer)
        other_item = JewelleryItem.objects.create(pledge=other_pledge, category="BANGLE")
        other_image = JewelleryImage.objects.create(
            jewellery_item=other_item, pledge=other_pledge, object_key="static/uploads/legacy.jpg"
        )
        deleted_pledge = Pledge.objects.create(
            pledge_code="GS-2026-0004", customer=other_customer, status=Pledge.Status.DELETED
        )
        deleted_item = JewelleryItem.objects.create(pledge=deleted_pledge)
        deleted_image = JewelleryImage.objects.create(
            jewellery_item=deleted_item, pledge=deleted_pledge, object_key="uploads/deleted.jpg"
        )
        post.return_value = httpx.Response(
            200,
            json={
                "model_version": "resnet50-imagenet1k-v2",
                "matches": [
                    {"image_id": str(deleted_image.id), "similarity_score": 0.99},
                    {"image_id": str(side.id), "similarity_score": 0.95},
                    {"image_id": str(front.id), "similarity_score": 0.93},
                    {"image_id": "not-a-uuid", "similarity_score": 0.9},
                    {"image_id": str(other_image.id), "similarity_score": 0.7},
                ],
            },
        )

        response = self.client.post(
            reverse("matching-search"),
            {"image": SimpleUploadedFile("query.png", b"image-bytes", content_type="image/png")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "COMPLETED")
        self.assertEqual(response.data["model_version"], "resnet50-imagenet1k-v2")
        self.assertTrue(response.data["search_id"])
        self.assertTrue(post.call_args.args[0].endswith("/pledge-images/match"))
        self.assertEqual(post.call_args.kwargs["params"], {"top_k": 50})

        matches = response.data["matches"]
        self.assertEqual([match["pledge_id"] for match in matches], ["GS-2026-0001", "GS-2026-0003"])
        self.assertEqual([match["rank"] for match in matches], [1, 2])
        best = matches[0]
        self.assertEqual(best["pledge_uuid"], str(self.pledge.id))
        self.assertEqual(best["similarity_score"], 0.95)
        self.assertEqual(best["matched_image_id"], str(side.id))
        self.assertEqual(best["customer_name"], "Test Customer")
        self.assertEqual(best["masked_aadhaar"], "XXXX XXXX 9012")
        self.assertNotIn("aadhaar_number", best)
        self.assertEqual(best["jewellery_category"], "RING")
        self.assertEqual(best["jewellery_description"], "Floral ring")
        self.assertIn("/api/v1/images/access/", best["stored_image_url"])
        self.assertEqual([image["id"] for image in best["images"]], [str(side.id), str(front.id)])
        self.assertIn("/api/v1/images/access/", matches[1]["stored_image_url"])

    @patch("apps.pledges.views.httpx.post")
    def test_matching_search_limits_results_to_top_k(self, post):
        item = JewelleryItem.objects.create(pledge=self.pledge)
        image = JewelleryImage.objects.create(jewellery_item=item, pledge=self.pledge, object_key="uploads/a.jpg")
        other_pledge = Pledge.objects.create(pledge_code="GS-2026-0003", customer=self.customer)
        other_item = JewelleryItem.objects.create(pledge=other_pledge)
        other_image = JewelleryImage.objects.create(
            jewellery_item=other_item, pledge=other_pledge, object_key="uploads/b.jpg"
        )
        post.return_value = httpx.Response(
            200,
            json={
                "matches": [
                    {"image_id": str(image.id), "similarity_score": 0.8},
                    {"image_id": str(other_image.id), "similarity_score": 0.7},
                ]
            },
        )

        response = self.client.post(
            reverse("matching-search"),
            {"image": SimpleUploadedFile("query.png", b"image-bytes", content_type="image/png"), "top_k": "1"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(post.call_args.kwargs["params"], {"top_k": 10})
        self.assertEqual([match["pledge_id"] for match in response.data["matches"]], ["GS-2026-0001"])

    @patch("apps.pledges.views.httpx.post", side_effect=httpx.ConnectError("offline"))
    def test_matching_search_reports_unavailable_ml_service(self, _post):
        response = self.client.post(
            reverse("matching-search"),
            {"image": SimpleUploadedFile("query.png", b"image-bytes", content_type="image/png")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 503)

    def test_matching_search_validates_top_k(self):
        response = self.client.post(
            reverse("matching-search"),
            {
                "image": SimpleUploadedFile("query.png", b"image-bytes", content_type="image/png"),
                "top_k": "51",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("top_k", response.data)

    def test_catalogue_item_details_and_images_are_served(self):
        output = BytesIO()
        Image.new("RGB", (4, 4), color="gold").save(output, format="PNG")
        webp_output = BytesIO()
        Image.new("RGB", (4, 4), color="gold").save(webp_output, format="WEBP")

        with tempfile.TemporaryDirectory() as dataset_root:
            item_directory = Path(dataset_root) / "Ring" / "Ring_001"
            item_directory.mkdir(parents=True)
            (item_directory / "1.png").write_bytes(output.getvalue())
            (item_directory / "2.webp").write_bytes(webp_output.getvalue())

            with override_settings(DATASET_DIR=Path(dataset_root)):
                detail = self.client.get(reverse("catalogue-item-detail", args=["Ring", "Ring_001"]))
                self.assertEqual(detail.status_code, 200)
                self.assertEqual(len(detail.data["images"]), 2)

                image = self.client.get(reverse("catalogue-item-image", args=["Ring", "Ring_001", "1.png"]))
                self.assertEqual(image.status_code, 200)
                self.assertEqual(image["Content-Type"], "image/png")
                self.assertEqual(b"".join(image.streaming_content), output.getvalue())

                webp = self.client.get(reverse("catalogue-item-image", args=["Ring", "Ring_001", "2.webp"]))
                self.assertEqual(webp.status_code, 200)
                self.assertEqual(webp["Content-Type"], "image/webp")
                self.assertEqual(b"".join(webp.streaming_content), webp_output.getvalue())

    def test_catalogue_detail_rejects_missing_and_unsafe_item_paths(self):
        with tempfile.TemporaryDirectory() as dataset_root:
            with override_settings(DATASET_DIR=Path(dataset_root)):
                missing = self.client.get(reverse("catalogue-item-detail", args=["Ring", "Missing"]))
                unsafe = self.client.get(reverse("catalogue-item-detail", args=["Ring", ".."]))

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(unsafe.status_code, 404)


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