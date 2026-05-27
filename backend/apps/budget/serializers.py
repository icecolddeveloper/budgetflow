import re
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.text import slugify
from rest_framework import serializers

from .models import Category, Transaction
from .services import create_transaction


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class CategorySerializer(serializers.ModelSerializer):
    remaining_budget = serializers.SerializerMethodField()
    utilization = serializers.SerializerMethodField()
    month_spending = serializers.SerializerMethodField()
    budget_progress = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "color",
            "balance",
            "monthly_budget",
            "is_primary",
            "remaining_budget",
            "utilization",
            "month_spending",
            "budget_progress",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "slug",
            "balance",
            "is_primary",
            "created_at",
            "updated_at",
        )

    def validate_color(self, value):
        if not HEX_COLOR_RE.match(value):
            raise serializers.ValidationError("Use a valid hex color like #0f766e.")
        return value

    def validate_monthly_budget(self, value):
        if value < 0:
            raise serializers.ValidationError("Monthly budget cannot be negative.")
        return value

    def _generate_slug(self, name):
        request = self.context["request"]
        base_slug = slugify(name) or "category"
        candidate = base_slug
        counter = 2
        queryset = Category.objects.filter(user=request.user)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        while queryset.filter(slug=candidate).exists():
            candidate = f"{base_slug}-{counter}"
            counter += 1
        return candidate

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        validated_data["slug"] = self._generate_slug(validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data and validated_data["name"] != instance.name:
            validated_data["slug"] = self._generate_slug(validated_data["name"])
        return super().update(instance, validated_data)

    def get_remaining_budget(self, obj):
        return max(obj.monthly_budget - obj.balance, Decimal("0.00"))

    def get_utilization(self, obj):
        if obj.monthly_budget == 0:
            return Decimal("0.00")
        progress = min(obj.balance / obj.monthly_budget, Decimal("1.00"))
        return round(progress * Decimal("100"), 2)

    def _month_spending(self, obj):
        value = getattr(obj, "month_spending", None)
        return value if value is not None else Decimal("0.00")

    def get_month_spending(self, obj):
        return self._month_spending(obj)

    def get_budget_progress(self, obj):
        if obj.monthly_budget == 0:
            return Decimal("0.00")
        progress = self._month_spending(obj) / obj.monthly_budget
        return round(progress * Decimal("100"), 2)


class TransactionSerializer(serializers.ModelSerializer):
    source_category_label = serializers.SerializerMethodField()
    destination_category_label = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = (
            "id",
            "kind",
            "amount",
            "description",
            "source_category",
            "destination_category",
            "source_category_label",
            "destination_category_label",
            "title",
            "occurred_at",
            "created_at",
        )

    def get_source_category_label(self, obj):
        if obj.source_category:
            return obj.source_category.name
        return obj.source_category_name

    def get_destination_category_label(self, obj):
        if obj.destination_category:
            return obj.destination_category.name
        return obj.destination_category_name

    def get_title(self, obj):
        if obj.kind == Transaction.Kind.DEPOSIT:
            return f"Income to {self.get_destination_category_label(obj)}"
        if obj.kind == Transaction.Kind.WITHDRAW:
            return f"Expense from {self.get_source_category_label(obj)}"
        return (
            f"Allocate {self.get_source_category_label(obj)} "
            f"to {self.get_destination_category_label(obj)}"
        )


class TransactionCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=Transaction.Kind.choices)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    source_category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.none(), required=False, allow_null=True
    )
    destination_category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.none(), required=False, allow_null=True
    )
    occurred_at = serializers.DateTimeField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.context["request"].user
        queryset = Category.objects.filter(user=user).order_by("name")
        self.fields["source_category"].queryset = queryset
        self.fields["destination_category"].queryset = queryset

    def validate(self, attrs):
        kind = attrs["kind"]
        if kind == Transaction.Kind.DEPOSIT:
            if not attrs.get("destination_category"):
                raise serializers.ValidationError(
                    {"destination_category": "Choose a category to fund."}
                )
            attrs["source_category"] = None
        if kind == Transaction.Kind.WITHDRAW:
            if not attrs.get("source_category"):
                raise serializers.ValidationError(
                    {"source_category": "Choose a category to spend from."}
                )
            attrs["destination_category"] = None
        if kind == Transaction.Kind.TRANSFER:
            if not attrs.get("source_category"):
                raise serializers.ValidationError(
                    {"source_category": "Choose a source category."}
                )
            if not attrs.get("destination_category"):
                raise serializers.ValidationError(
                    {"destination_category": "Choose a destination category."}
                )
            if attrs["source_category"] == attrs["destination_category"]:
                raise serializers.ValidationError(
                    {"destination_category": "Source and destination must be different."}
                )
        return attrs

    def create(self, validated_data):
        try:
            return create_transaction(
                user=self.context["request"].user, **validated_data
            )
        except DjangoValidationError as exc:
            detail = getattr(exc, "message_dict", None) or exc.messages
            raise serializers.ValidationError(detail)

    def to_representation(self, instance):
        return TransactionSerializer(instance, context=self.context).data
