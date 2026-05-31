from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Category(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90)
    description = models.CharField(max_length=160, blank=True)
    color = models.CharField(max_length=7, default="#0f766e")
    icon = models.CharField(max_length=40, default="wallet")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    monthly_budget = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=("user", "slug"), name="unique_category_slug_per_user"),
            models.UniqueConstraint(
                fields=("user",),
                condition=Q(is_primary=True),
                name="one_primary_category_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Transaction(models.Model):
    class Kind(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        WITHDRAW = "withdraw", "Withdraw"
        TRANSFER = "transfer", "Transfer"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    source_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outgoing_transactions",
    )
    destination_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_transactions",
    )
    source_category_name = models.CharField(max_length=80, blank=True)
    destination_category_name = models.CharField(max_length=80, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    recurring_rule = models.ForeignKey(
        "RecurringRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_transactions",
    )

    class Meta:
        ordering = ("-occurred_at", "-created_at")

    def __str__(self):
        return f"{self.kind} {self.amount} for {self.user.username}"


class RecurringRule(models.Model):
    class Frequency(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Every two weeks"
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_rules",
    )
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=12, choices=Transaction.Kind.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    source_category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="outgoing_recurring_rules",
    )
    destination_category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="incoming_recurring_rules",
    )
    frequency = models.CharField(max_length=12, choices=Frequency.choices)
    next_run_at = models.DateTimeField()
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("next_run_at", "name")

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()}) for {self.user.username}"
