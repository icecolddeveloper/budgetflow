import calendar
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Category, RecurringRule, Transaction


DEFAULT_CATEGORY_TEMPLATES = [
    {
        "name": "Wallet",
        "description": "Unallocated income waiting to be budgeted.",
        "color": "#0f172a",
        "icon": "wallet",
        "monthly_budget": Decimal("0.00"),
        "is_primary": True,
    },
    {
        "name": "Food",
        "description": "Groceries, restaurants, and snacks.",
        "color": "#f97316",
        "icon": "utensils-crossed",
        "monthly_budget": Decimal("400.00"),
    },
    {
        "name": "Transport",
        "description": "Fuel, rideshares, public transit, and parking.",
        "color": "#0f766e",
        "icon": "car-front",
        "monthly_budget": Decimal("180.00"),
    },
    {
        "name": "Rent",
        "description": "Housing and living essentials.",
        "color": "#1d4ed8",
        "icon": "building-2",
        "monthly_budget": Decimal("1200.00"),
    },
    {
        "name": "Savings",
        "description": "Long-term goals and emergency reserves.",
        "color": "#16a34a",
        "icon": "piggy-bank",
        "monthly_budget": Decimal("500.00"),
    },
    {
        "name": "Entertainment",
        "description": "Streaming, hobbies, and fun money.",
        "color": "#dc2626",
        "icon": "party-popper",
        "monthly_budget": Decimal("150.00"),
    },
]


def seed_default_categories(user):
    existing_names = set(user.categories.values_list("name", flat=True))
    categories_to_create = []
    for template in DEFAULT_CATEGORY_TEMPLATES:
        if template["name"] in existing_names:
            continue
        categories_to_create.append(Category(user=user, slug=template["name"].lower(), **template))
    if categories_to_create:
        Category.objects.bulk_create(categories_to_create)


@transaction.atomic
def create_transaction(
    *,
    user,
    kind,
    amount,
    description="",
    source_category=None,
    destination_category=None,
    occurred_at=None,
    recurring_rule=None,
):
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValidationError({"amount": "Amount must be greater than zero."})

    occurred_at = occurred_at or timezone.now()
    description = description.strip()

    if kind == Transaction.Kind.DEPOSIT:
        if not destination_category:
            raise ValidationError({"destination_category": "Choose a category to fund."})
        category = Category.objects.select_for_update().get(pk=destination_category.pk, user=user)
        category.balance += amount
        category.save(update_fields=["balance", "updated_at"])
        return Transaction.objects.create(
            user=user,
            kind=kind,
            amount=amount,
            description=description,
            destination_category=category,
            destination_category_name=category.name,
            occurred_at=occurred_at,
            recurring_rule=recurring_rule,
        )

    if kind == Transaction.Kind.WITHDRAW:
        if not source_category:
            raise ValidationError({"source_category": "Choose a category to spend from."})
        category = Category.objects.select_for_update().get(pk=source_category.pk, user=user)
        if category.balance < amount:
            raise ValidationError(
                {
                    "amount": (
                        f"{category.name} only has ${category.balance:.2f} available. "
                        "Move funds into it from Wallet before withdrawing."
                    )
                }
            )
        category.balance -= amount
        category.save(update_fields=["balance", "updated_at"])
        return Transaction.objects.create(
            user=user,
            kind=kind,
            amount=amount,
            description=description,
            source_category=category,
            source_category_name=category.name,
            occurred_at=occurred_at,
            recurring_rule=recurring_rule,
        )

    if not source_category:
        raise ValidationError({"source_category": "Choose a source category."})
    if not destination_category:
        raise ValidationError({"destination_category": "Choose a destination category."})
    if source_category.pk == destination_category.pk:
        raise ValidationError({"destination_category": "Source and destination must be different."})

    source = Category.objects.select_for_update().get(pk=source_category.pk, user=user)
    destination = Category.objects.select_for_update().get(pk=destination_category.pk, user=user)

    if source.balance < amount:
        raise ValidationError(
            {
                "amount": (
                    f"{source.name} only has ${source.balance:.2f} available to transfer."
                )
            }
        )

    source.balance -= amount
    destination.balance += amount
    source.save(update_fields=["balance", "updated_at"])
    destination.save(update_fields=["balance", "updated_at"])

    return Transaction.objects.create(
        user=user,
        kind=kind,
        amount=amount,
        description=description,
        source_category=source,
        destination_category=destination,
        source_category_name=source.name,
        destination_category_name=destination.name,
        occurred_at=occurred_at,
        recurring_rule=recurring_rule,
    )


def advance_next_run(current, frequency):
    if frequency == RecurringRule.Frequency.WEEKLY:
        return current + timedelta(days=7)
    if frequency == RecurringRule.Frequency.BIWEEKLY:
        return current + timedelta(days=14)
    if frequency == RecurringRule.Frequency.MONTHLY:
        month_index = current.month - 1 + 1
        year = current.year + month_index // 12
        month = month_index % 12 + 1
        day = min(current.day, calendar.monthrange(year, month)[1])
        return current.replace(year=year, month=month, day=day)
    if frequency == RecurringRule.Frequency.YEARLY:
        try:
            return current.replace(year=current.year + 1)
        except ValueError:
            return current.replace(year=current.year + 1, day=28)
    raise ValueError(f"Unsupported frequency: {frequency}")


MAX_CATCHUP_RUNS = 24


def process_due_recurring_rules(user):
    now = timezone.now()
    results = []

    rule_ids = list(
        RecurringRule.objects.filter(
            user=user,
            is_active=True,
            next_run_at__lte=now,
        ).values_list("pk", flat=True)
    )

    for rule_id in rule_ids:
        rule = RecurringRule.objects.filter(pk=rule_id).first()
        if rule is None:
            continue
        runs = 0
        while (
            rule.is_active
            and rule.next_run_at <= now
            and runs < MAX_CATCHUP_RUNS
            and (rule.end_date is None or rule.next_run_at.date() <= rule.end_date)
        ):
            try:
                created = create_transaction(
                    user=user,
                    kind=rule.kind,
                    amount=rule.amount,
                    description=rule.description or rule.name,
                    source_category=rule.source_category,
                    destination_category=rule.destination_category,
                    occurred_at=rule.next_run_at,
                    recurring_rule=rule,
                )
                results.append(created)
                rule.last_run_at = rule.next_run_at
                rule.last_error = ""
                rule.next_run_at = advance_next_run(rule.next_run_at, rule.frequency)
                rule.save(
                    update_fields=[
                        "last_run_at",
                        "last_error",
                        "next_run_at",
                        "updated_at",
                    ]
                )
                runs += 1
            except ValidationError as exc:
                detail = getattr(exc, "message_dict", None) or exc.messages
                if isinstance(detail, dict):
                    message = " ".join(str(value) for sublist in detail.values() for value in sublist)
                else:
                    message = " ".join(str(value) for value in detail)
                rule.last_error = message[:255]
                rule.save(update_fields=["last_error", "updated_at"])
                break

        if rule.end_date is not None and rule.next_run_at.date() > rule.end_date:
            rule.is_active = False
            rule.save(update_fields=["is_active", "updated_at"])

    return results
