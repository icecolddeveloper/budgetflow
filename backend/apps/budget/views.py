from collections import OrderedDict
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, RecurringRule, Transaction
from .serializers import (
    CategorySerializer,
    RecurringRuleSerializer,
    TransactionCreateSerializer,
    TransactionSerializer,
)
from .services import process_due_recurring_rules


def shift_month(value, offset):
    month_index = value.month - 1 + offset
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return value.replace(year=year, month=month, day=1)


def categories_with_month_spending(user):
    start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return Category.objects.filter(user=user).annotate(
        month_spending=Sum(
            "outgoing_transactions__amount",
            filter=Q(
                outgoing_transactions__kind=Transaction.Kind.WITHDRAW,
                outgoing_transactions__occurred_at__gte=start_of_month,
            ),
        )
    )


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return categories_with_month_spending(self.request.user).order_by("-balance", "name")

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        if category.is_primary:
            raise ValidationError(
                {"detail": "The Wallet category cannot be deleted."}
            )
        if category.balance != 0:
            raise ValidationError(
                {"detail": "Move or withdraw the remaining balance before deleting this category."}
            )
        return super().destroy(request, *args, **kwargs)


class TransactionViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        process_due_recurring_rules(request.user)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user).select_related(
            "source_category", "destination_category"
        )
        limit = self.request.query_params.get("limit")
        if limit and limit.isdigit():
            return queryset[: int(limit)]
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return TransactionCreateSerializer
        return TransactionSerializer


class RecurringRuleViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RecurringRule.objects.filter(user=self.request.user).select_related(
            "source_category", "destination_category"
        )


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        process_due_recurring_rules(request.user)
        categories = list(categories_with_month_spending(request.user).order_by("-balance", "name"))
        transactions = list(
            Transaction.objects.filter(user=request.user)
            .select_related("source_category", "destination_category")
            .order_by("-occurred_at", "-created_at")
        )

        total_balance = sum((category.balance for category in categories), Decimal("0.00"))
        start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        monthly_inflow = Decimal("0.00")
        monthly_outflow = Decimal("0.00")
        spending_by_category = {}
        month_buckets = OrderedDict()
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for offset in range(5, -1, -1):
            month = shift_month(current_month, -offset)
            month_key = month.strftime("%Y-%m")
            month_buckets[month_key] = {
                "month": month.strftime("%b"),
                "deposits": Decimal("0.00"),
                "spending": Decimal("0.00"),
            }

        for transaction in transactions:
            if transaction.occurred_at >= start_of_month:
                if transaction.kind == Transaction.Kind.DEPOSIT:
                    monthly_inflow += transaction.amount
                else:
                    monthly_outflow += transaction.amount
                    label = transaction.source_category_name or "Uncategorized"
                    if transaction.source_category:
                        label = transaction.source_category.name
                    current_total = spending_by_category.get(label, Decimal("0.00"))
                    spending_by_category[label] = current_total + transaction.amount

            month_key = transaction.occurred_at.strftime("%Y-%m")
            if month_key in month_buckets:
                if transaction.kind == Transaction.Kind.DEPOSIT:
                    month_buckets[month_key]["deposits"] += transaction.amount
                else:
                    month_buckets[month_key]["spending"] += transaction.amount

        color_map = {category.name: category.color for category in categories}
        spending_breakdown = [
            {
                "category": name,
                "total": total,
                "color": color_map.get(name, "#0f172a"),
            }
            for name, total in sorted(spending_by_category.items(), key=lambda item: item[1], reverse=True)
        ][:6]

        recent_transactions = transactions[:8]
        payload = {
            "total_balance": total_balance,
            "monthly_inflow": monthly_inflow,
            "monthly_outflow": monthly_outflow,
            "category_count": len(categories),
            "categories": CategorySerializer(categories, many=True, context={"request": request}).data,
            "recent_transactions": TransactionSerializer(
                recent_transactions, many=True, context={"request": request}
            ).data,
            "spending_breakdown": spending_breakdown,
            "cashflow_trend": list(month_buckets.values()),
        }
        return Response(payload, status=status.HTTP_200_OK)
