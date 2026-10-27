import re
import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Pledge
from .serializers import OnboardingSerializer, PledgeDetailSerializer, PledgeListSerializer


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
        return Response(PledgeDetailSerializer(pledge).data, status=status.HTTP_201_CREATED)


class ImageUploadView(APIView):
    permission_classes = [AllowAny]
    max_upload_bytes = 10 * 1024 * 1024
    image_formats = {
        "JPEG": ("jpg", "image/jpeg"),
        "PNG": ("png", "image/png"),
        "WEBP": ("webp", "image/webp"),
    }

    def post(self, request):
        uploaded_file = request.FILES.get("image")
        if uploaded_file is None:
            return Response({"image": "Choose an image to upload."}, status=status.HTTP_400_BAD_REQUEST)
        if uploaded_file.size > self.max_upload_bytes:
            return Response(
                {"image": "Image files must be 10 MB or smaller."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content = uploaded_file.read()
        try:
            with Image.open(BytesIO(content)) as image:
                image_format = image.format
                image.verify()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            return Response(
                {"image": "The uploaded file is not a valid image."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        image_details = self.image_formats.get(image_format or "")
        if image_details is None:
            return Response(
                {"image": "Only JPG, PNG, and WEBP images are supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extension, content_type = image_details
        object_key = f"uploads/{uuid.uuid4().hex}.{extension}"
        saved_key = default_storage.save(object_key, ContentFile(content))
        return Response(
            {
                "object_key": saved_key,
                "url": request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_key}"),
                "original_filename": Path(uploaded_file.name).name[:255],
                "content_type": content_type,
                "file_size_bytes": len(content),
            },
            status=status.HTTP_201_CREATED,
        )