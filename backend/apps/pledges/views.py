import re

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