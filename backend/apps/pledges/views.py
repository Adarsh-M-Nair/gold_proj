import logging
import re
import uuid
from pathlib import Path

import httpx
from botocore.exceptions import BotoCoreError
from django.conf import settings
from django.core import signing
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.urls import reverse
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jewellery.indexing import PledgeImageUnavailable, read_pledge_image
from apps.jewellery.models import JewelleryImage
from .image_storage import (
    MAX_UPLOAD_BYTES,
    PRIVATE_IMAGE_SALT,
    InvalidImageUpload,
    create_upload_request,
    inspect_image_content,
    object_storage_enabled,
    private_image_url,
    save_uploaded_image,
    validate_upload_metadata,
)
from .models import Pledge
from .serializers import OnboardingSerializer, PledgeDetailSerializer, PledgeListSerializer, mask_aadhaar


logger = logging.getLogger(__name__)
CATALOGUE_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
CATALOGUE_IMAGE_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def catalogue_item_directory(category, item_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", category) or not re.fullmatch(r"[A-Za-z0-9_-]+", item_id):
        return None

    dataset_root = Path(settings.DATASET_DIR).resolve()
    item_directory = (dataset_root / category / item_id).resolve()
    if dataset_root not in item_directory.parents or not item_directory.is_dir():
        return None
    return item_directory


def catalogue_images(item_directory):
    return sorted(
        (
            path
            for path in item_directory.iterdir()
            if path.is_file() and path.suffix.lower() in CATALOGUE_IMAGE_SUFFIXES
            and item_directory in path.resolve().parents
        ),
        key=lambda path: path.name.lower(),
    )


def pledge_image_url(request, object_key):
    return private_image_url(request, object_key)


class PledgePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class PledgeListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    pagination_class = PledgePagination
    serializer_class = PledgeListSerializer

    def get_queryset(self):
        queryset = Pledge.objects.select_related("customer").prefetch_related("items__images")
        requested_status = self.request.query_params.get("status")
        if requested_status:
            valid_statuses = {choice[0] for choice in Pledge.Status.choices}
            if requested_status not in valid_statuses:
                return queryset.none()
            queryset = queryset.filter(status=requested_status)
        else:
            queryset = queryset.exclude(status=Pledge.Status.DELETED)

        query = self.request.query_params.get("search", "").strip()
        if query:
            search_filter = (
                Q(customer__full_name__icontains=query)
                | Q(customer__phone_number__icontains=query)
                | Q(pledge_code__icontains=query)
            )
            aadhaar_digits = re.sub(r"\D", "", query)
            if aadhaar_digits:
                search_filter |= Q(customer__aadhaar_number__icontains=aadhaar_digits)
            queryset = queryset.filter(search_filter)
        return queryset.order_by("-created_at", "-id")


class PledgeDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = Pledge.objects.select_related("customer").prefetch_related("items__images")
    serializer_class = PledgeDetailSerializer
    lookup_field = "id"

    def destroy(self, request, *args, **kwargs):
        pledge = self.get_object()
        if pledge.status != Pledge.Status.DELETED:
            pledge.status = Pledge.Status.DELETED
            pledge.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomerOnboardingView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pledge = serializer.save()
        pledge = Pledge.objects.select_related("customer").prefetch_related("items__images").get(pk=pledge.pk)
        return Response(
            PledgeDetailSerializer(pledge, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class PresignedImageUploadView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            filename, content_type, file_size = validate_upload_metadata(request.data)
            upload = create_upload_request(request, filename, content_type, file_size)
        except InvalidImageUpload as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        except BotoCoreError:
            logger.exception("Could not create an object-storage upload URL")
            return Response(
                {"detail": "Image storage is unavailable. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(upload, status=status.HTTP_200_OK)


class ImageUploadView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uploaded_file = request.FILES.get("image")
        if uploaded_file is None:
            return Response({"image": "Choose an image to upload."}, status=status.HTTP_400_BAD_REQUEST)
        if uploaded_file.size > MAX_UPLOAD_BYTES:
            return Response(
                {"image": "Image files must be 10 MB or smaller."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content = uploaded_file.read()
        try:
            filename = Path(uploaded_file.name).name[:255]
            object_key, details = save_uploaded_image(content)
        except InvalidImageUpload as error:
            return Response(
                {"image": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except BotoCoreError:
            logger.exception("Could not save an uploaded image")
            return Response(
                {"detail": "Image storage is unavailable. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "object_key": object_key,
                "url": private_image_url(request, object_key),
                "original_filename": filename,
                "content_type": details["content_type"],
                "file_size_bytes": details["file_size_bytes"],
                "checksum_sha256": details["checksum_sha256"],
            },
            status=status.HTTP_201_CREATED,
        )


class PrivateImageAccessView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            object_key = signing.loads(token, salt=PRIVATE_IMAGE_SALT, max_age=300)
            content = read_pledge_image(JewelleryImage(object_key=object_key))
        except (
            signing.BadSignature,
            signing.SignatureExpired,
            FileNotFoundError,
            OSError,
            PledgeImageUnavailable,
            ValueError,
        ):
            raise Http404("Image not found.")
        try:
            details = inspect_image_content(content)
        except InvalidImageUpload:
            raise Http404("Image not found.")
        response = HttpResponse(content, content_type=details["content_type"])
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class MatchingSearchView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    max_upload_bytes = 10 * 1024 * 1024
    max_top_k = 50
    # Several images can belong to one pledge, so fetch extra candidates before grouping by pledge.
    candidate_multiplier = 10
    max_candidates = 200

    def post(self, request):
        uploaded_file = request.FILES.get("image")
        if uploaded_file is None:
            return Response({"image": "Choose an image to search."}, status=status.HTTP_400_BAD_REQUEST)
        if uploaded_file.size > self.max_upload_bytes:
            return Response(
                {"image": "Image files must be 10 MB or smaller."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            top_k = int(request.data.get("top_k", 5))
        except (TypeError, ValueError):
            return Response({"top_k": "Enter a whole number between 1 and 50."}, status=status.HTTP_400_BAD_REQUEST)
        if not 1 <= top_k <= self.max_top_k:
            return Response({"top_k": "Enter a whole number between 1 and 50."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            upstream = httpx.post(
                f"{settings.ML_SERVICE_URL}/pledge-images/match",
                params={"top_k": min(top_k * self.candidate_multiplier, self.max_candidates)},
                files={
                    "image": (
                        Path(uploaded_file.name).name,
                        uploaded_file.read(),
                        uploaded_file.content_type or "application/octet-stream",
                    )
                },
                timeout=60.0,
            )
        except httpx.RequestError:
            logger.exception("Could not reach the configured ML matching service")
            return Response(
                {"detail": "The matching service is unavailable. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not upstream.is_success:
            if upstream.status_code < 500:
                try:
                    error_body = upstream.json()
                except ValueError:
                    error_body = {"detail": "The ML service rejected the image."}
                return Response(error_body, status=upstream.status_code)
            logger.error("ML matching service returned HTTP %s", upstream.status_code)
            return Response(
                {"detail": "The matching service failed to process the image."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            result = upstream.json()
        except ValueError:
            logger.error("ML matching service returned a non-JSON success response")
            return Response(
                {"detail": "The matching service returned an invalid response."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if not isinstance(result, dict) or not isinstance(result.get("matches"), list):
            logger.error("ML matching service returned an unexpected response shape")
            return Response(
                {"detail": "The matching service returned an invalid response."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        result["matches"] = self.pledge_matches(request, result["matches"], top_k)
        result["search_id"] = str(uuid.uuid4())
        result["status"] = "COMPLETED"
        return Response(result, status=status.HTTP_200_OK)

    def pledge_matches(self, request, candidates, top_k):
        ranked = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            score = candidate.get("similarity_score")
            try:
                image_id = uuid.UUID(str(candidate.get("image_id")))
            except ValueError:
                continue
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                ranked.append((image_id, float(score)))

        images = (
            JewelleryImage.objects.filter(id__in=[image_id for image_id, _ in ranked])
            .exclude(pledge__status=Pledge.Status.DELETED)
            .select_related("pledge__customer", "jewellery_item")
            .prefetch_related("pledge__images")
        )
        images_by_id = {image.id: image for image in images}

        matches = []
        matched_pledges = set()
        for image_id, score in ranked:
            image = images_by_id.get(image_id)
            if image is None or image.pledge_id in matched_pledges:
                continue
            matched_pledges.add(image.pledge_id)
            matches.append(self.pledge_match(request, image, score, rank=len(matches) + 1))
            if len(matches) == top_k:
                break
        return matches

    def pledge_match(self, request, image, score, rank):
        pledge = image.pledge
        customer = pledge.customer
        item = image.jewellery_item
        gallery = [image] + [other for other in pledge.images.all() if other.id != image.id]
        return {
            "result_id": str(uuid.uuid4()),
            "rank": rank,
            "similarity_score": max(0.0, min(1.0, score)),
            "matched_image_id": str(image.id),
            "pledge_uuid": str(pledge.id),
            "pledge_id": pledge.pledge_code,
            "pledge_status": pledge.status,
            "registered_at": pledge.created_at.isoformat(),
            "customer_name": customer.full_name,
            "phone_number": customer.phone_number,
            "masked_aadhaar": mask_aadhaar(customer.aadhaar_number),
            "jewellery_item_id": str(item.id),
            "jewellery_category": item.category,
            "jewellery_description": item.description,
            "purity": item.purity,
            "stored_image_url": pledge_image_url(request, image.object_key),
            "images": [
                {"id": str(other.id), "url": pledge_image_url(request, other.object_key)} for other in gallery
            ],
        }


class CatalogueItemDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, category, item_id):
        item_directory = catalogue_item_directory(category, item_id)
        if item_directory is None:
            raise Http404("Catalogue item not found.")

        images = catalogue_images(item_directory)
        if not images:
            raise Http404("Catalogue item images not found.")

        return Response(
            {
                "category": category,
                "item_id": item_id,
                "images": [
                    {
                        "filename": image.name,
                        "url": request.build_absolute_uri(
                            reverse("catalogue-item-image", args=[category, item_id, image.name])
                        ),
                    }
                    for image in images
                ],
            }
        )


class CatalogueItemImageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, category, item_id, filename):
        item_directory = catalogue_item_directory(category, item_id)
        if item_directory is None:
            raise Http404("Catalogue item not found.")

        image = next((path for path in catalogue_images(item_directory) if path.name == filename), None)
        if image is None:
            raise Http404("Catalogue image not found.")

        return FileResponse(image.open("rb"), content_type=CATALOGUE_IMAGE_CONTENT_TYPES[image.suffix.lower()])