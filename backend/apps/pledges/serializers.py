import re

from django.db import transaction
from rest_framework import serializers

from apps.customers.models import Customer
from apps.jewellery.models import JewelleryImage, JewelleryItem
from .models import Pledge
from .services import generate_pledge_code


def mask_aadhaar(value):
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    return f"XXXX XXXX {digits[-4:]}"


class CustomerSummarySerializer(serializers.ModelSerializer):
    masked_aadhaar = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ["id", "full_name", "phone_number", "masked_aadhaar"]

    def get_masked_aadhaar(self, obj):
        return mask_aadhaar(obj.aadhaar_number)


class JewelleryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = JewelleryImage
        fields = [
            "id",
            "object_key",
            "thumbnail_object_key",
            "original_filename",
            "content_type",
            "file_size_bytes",
            "capture_source",
            "image_type",
            "embedding_status",
            "created_at",
        ]


class JewelleryItemSerializer(serializers.ModelSerializer):
    images = JewelleryImageSerializer(many=True, read_only=True)

    class Meta:
        model = JewelleryItem
        fields = ["id", "category", "description", "weight_grams", "purity", "status", "images"]


class PledgeListSerializer(serializers.ModelSerializer):
    pledge_id = serializers.CharField(source="pledge_code", read_only=True)
    customer = CustomerSummarySerializer(read_only=True)
    registered_at = serializers.DateTimeField(source="created_at", read_only=True)
    primary_photo = serializers.SerializerMethodField()

    class Meta:
        model = Pledge
        fields = ["id", "pledge_id", "pledge_code", "customer", "registered_at", "status", "primary_photo"]

    def get_primary_photo(self, obj):
        for item in obj.items.all():
            image = next(iter(item.images.all()), None)
            if image:
                return image.thumbnail_object_key or image.object_key
        return ""


class PledgeDetailSerializer(PledgeListSerializer):
    items = JewelleryItemSerializer(many=True, read_only=True)

    class Meta(PledgeListSerializer.Meta):
        fields = PledgeListSerializer.Meta.fields + [
            "branch_id",
            "pledge_date",
            "total_weight_grams",
            "estimated_value",
            "items",
            "updated_at",
        ]


class CustomerInputSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=15)
    aadhaar_number = serializers.CharField(max_length=14, write_only=True)

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_phone_number(self, value):
        digits = re.sub(r"\D", "", value)
        if len(digits) != 10:
            raise serializers.ValidationError("Enter a 10-digit Indian mobile number.")
        return digits

    def validate_aadhaar_number(self, value):
        digits = re.sub(r"\D", "", value)
        if len(digits) != 12:
            raise serializers.ValidationError("Enter a 12-digit Aadhaar number.")
        return digits


class PledgeInputSerializer(serializers.Serializer):
    branch_id = serializers.UUIDField(required=False, allow_null=True)
    pledge_date = serializers.DateField(required=False)
    total_weight_grams = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, allow_null=True)
    estimated_value = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True)


class JewelleryItemInputSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=50, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    weight_grams = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, allow_null=True)
    purity = serializers.CharField(max_length=20, required=False, allow_blank=True)


class JewelleryImageInputSerializer(serializers.Serializer):
    object_key = serializers.CharField(max_length=1024)
    thumbnail_object_key = serializers.CharField(max_length=1024, required=False, allow_blank=True)
    original_filename = serializers.CharField(max_length=255, required=False, allow_blank=True)
    content_type = serializers.CharField(max_length=100, required=False, default="application/octet-stream")
    file_size_bytes = serializers.IntegerField(min_value=0, required=False, default=0)
    checksum_sha256 = serializers.CharField(max_length=64, required=False, allow_blank=True)
    capture_source = serializers.ChoiceField(choices=JewelleryImage.CaptureSource.choices, required=False)
    image_type = serializers.ChoiceField(choices=JewelleryImage.ImageType.choices, required=False)


class OnboardingSerializer(serializers.Serializer):
    customer = CustomerInputSerializer()
    pledge = PledgeInputSerializer(required=False, default=dict)
    jewellery_item = JewelleryItemInputSerializer(required=False, default=dict)
    images = JewelleryImageInputSerializer(many=True, allow_empty=False)

    @transaction.atomic
    def create(self, validated_data):
        customer = Customer.objects.create(**validated_data["customer"])
        pledge_data = validated_data.get("pledge", {})
        pledge = Pledge.objects.create(
            customer=customer,
            pledge_code=generate_pledge_code(),
            **pledge_data,
        )
        item = JewelleryItem.objects.create(pledge=pledge, **validated_data.get("jewellery_item", {}))
        for image_data in validated_data["images"]:
            JewelleryImage.objects.create(
                jewellery_item=item,
                pledge=pledge,
                **image_data,
            )
        return pledge