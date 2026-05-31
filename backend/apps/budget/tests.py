from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.budget.models import Category, RecurringRule, Transaction
from apps.budget.services import (
    advance_next_run,
    create_transaction,
    process_due_recurring_rules,
)


def make_category(user, name, slug, *, balance="0.00", monthly_budget="0.00", color="#0f766e"):
    return Category.objects.create(
        user=user,
        name=name,
        slug=slug,
        color=color,
        icon="wallet",
        balance=Decimal(balance),
        monthly_budget=Decimal(monthly_budget),
    )


class TransactionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sam", password="StrongPass123")
        self.food = make_category(
            self.user, "Food", "food", balance="250.00", monthly_budget="300.00", color="#f97316"
        )
        self.savings = make_category(
            self.user, "Savings", "savings", balance="50.00", monthly_budget="500.00", color="#16a34a"
        )

    def test_transfer_moves_balance_between_categories(self):
        transaction = create_transaction(
            user=self.user,
            kind=Transaction.Kind.TRANSFER,
            amount="25.00",
            description="Weekly sweep",
            source_category=self.food,
            destination_category=self.savings,
        )

        self.food.refresh_from_db()
        self.savings.refresh_from_db()

        self.assertEqual(transaction.kind, Transaction.Kind.TRANSFER)
        self.assertEqual(self.food.balance, Decimal("225.00"))
        self.assertEqual(self.savings.balance, Decimal("75.00"))

    def test_deposit_adds_to_destination_balance(self):
        transaction = create_transaction(
            user=self.user,
            kind=Transaction.Kind.DEPOSIT,
            amount="40.00",
            destination_category=self.savings,
        )

        self.savings.refresh_from_db()
        self.assertEqual(transaction.kind, Transaction.Kind.DEPOSIT)
        self.assertEqual(self.savings.balance, Decimal("90.00"))
        self.assertEqual(transaction.destination_category_name, "Savings")
        self.assertIsNone(transaction.source_category)

    def test_withdraw_subtracts_from_source_balance(self):
        transaction = create_transaction(
            user=self.user,
            kind=Transaction.Kind.WITHDRAW,
            amount="30.00",
            source_category=self.food,
        )

        self.food.refresh_from_db()
        self.assertEqual(transaction.kind, Transaction.Kind.WITHDRAW)
        self.assertEqual(self.food.balance, Decimal("220.00"))
        self.assertEqual(transaction.source_category_name, "Food")
        self.assertIsNone(transaction.destination_category)

    def test_withdraw_rejects_insufficient_balance(self):
        with self.assertRaises(ValidationError) as ctx:
            create_transaction(
                user=self.user,
                kind=Transaction.Kind.WITHDRAW,
                amount="9999.00",
                source_category=self.food,
            )

        self.assertIn("amount", ctx.exception.message_dict)
        self.food.refresh_from_db()
        self.assertEqual(self.food.balance, Decimal("250.00"))

    def test_transfer_rejects_insufficient_balance(self):
        with self.assertRaises(ValidationError):
            create_transaction(
                user=self.user,
                kind=Transaction.Kind.TRANSFER,
                amount="9999.00",
                source_category=self.food,
                destination_category=self.savings,
            )

        self.food.refresh_from_db()
        self.savings.refresh_from_db()
        self.assertEqual(self.food.balance, Decimal("250.00"))
        self.assertEqual(self.savings.balance, Decimal("50.00"))

    def test_transfer_rejects_same_source_and_destination(self):
        with self.assertRaises(ValidationError) as ctx:
            create_transaction(
                user=self.user,
                kind=Transaction.Kind.TRANSFER,
                amount="10.00",
                source_category=self.food,
                destination_category=self.food,
            )

        self.assertIn("destination_category", ctx.exception.message_dict)

    def test_deposit_requires_destination_category(self):
        with self.assertRaises(ValidationError) as ctx:
            create_transaction(
                user=self.user,
                kind=Transaction.Kind.DEPOSIT,
                amount="10.00",
            )

        self.assertIn("destination_category", ctx.exception.message_dict)

    def test_withdraw_requires_source_category(self):
        with self.assertRaises(ValidationError) as ctx:
            create_transaction(
                user=self.user,
                kind=Transaction.Kind.WITHDRAW,
                amount="10.00",
            )

        self.assertIn("source_category", ctx.exception.message_dict)

    def test_zero_amount_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_transaction(
                user=self.user,
                kind=Transaction.Kind.DEPOSIT,
                amount="0.00",
                destination_category=self.savings,
            )

    def test_negative_amount_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_transaction(
                user=self.user,
                kind=Transaction.Kind.DEPOSIT,
                amount="-5.00",
                destination_category=self.savings,
            )


class CategoryApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jess", password="StrongPass123")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_destroy_rejects_category_with_nonzero_balance(self):
        category = make_category(self.user, "Gifts", "gifts", balance="12.50")

        response = self.client.delete(f"/api/categories/{category.pk}/")

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Category.objects.filter(pk=category.pk).exists())

    def test_destroy_rejects_primary_category(self):
        wallet = Category.objects.create(
            user=self.user,
            name="Wallet",
            slug="wallet",
            color="#0f172a",
            icon="wallet",
            is_primary=True,
        )

        response = self.client.delete(f"/api/categories/{wallet.pk}/")

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Category.objects.filter(pk=wallet.pk).exists())

    def test_destroy_allows_empty_category(self):
        category = make_category(self.user, "Gifts", "gifts")

        response = self.client.delete(f"/api/categories/{category.pk}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_queryset_is_scoped_to_request_user(self):
        make_category(self.user, "Mine", "mine")
        other = User.objects.create_user(username="other", password="StrongPass123")
        make_category(other, "Theirs", "theirs")

        response = self.client.get("/api/categories/")

        self.assertEqual(response.status_code, 200)
        names = {item["name"] for item in response.json()}
        self.assertEqual(names, {"Mine"})

    def test_list_reports_month_to_date_spending_and_progress(self):
        food = make_category(
            self.user, "Food", "food", balance="100.00", monthly_budget="200.00"
        )
        # Withdraw this month — counts toward month_spending.
        create_transaction(
            user=self.user,
            kind=Transaction.Kind.WITHDRAW,
            amount="50.00",
            source_category=food,
        )
        # A withdraw stamped to last month — must NOT count.
        stale = create_transaction(
            user=self.user,
            kind=Transaction.Kind.WITHDRAW,
            amount="40.00",
            source_category=food,
        )
        Transaction.objects.filter(pk=stale.pk).update(
            occurred_at=timezone.now().replace(day=1) - timedelta(days=5)
        )

        response = self.client.get("/api/categories/")

        self.assertEqual(response.status_code, 200)
        item = next(row for row in response.json() if row["name"] == "Food")
        self.assertEqual(Decimal(item["month_spending"]), Decimal("50.00"))
        self.assertEqual(Decimal(item["budget_progress"]), Decimal("25.00"))

    def test_budget_progress_exceeds_100_when_over_budget(self):
        rent = make_category(
            self.user, "Rent", "rent", balance="1000.00", monthly_budget="100.00"
        )
        create_transaction(
            user=self.user,
            kind=Transaction.Kind.WITHDRAW,
            amount="150.00",
            source_category=rent,
        )

        response = self.client.get("/api/categories/")

        item = next(row for row in response.json() if row["name"] == "Rent")
        self.assertEqual(Decimal(item["month_spending"]), Decimal("150.00"))
        self.assertGreater(Decimal(item["budget_progress"]), Decimal("100.00"))


class TransactionApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="kai", password="StrongPass123")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.wallet = make_category(self.user, "Wallet", "wallet", balance="500.00")

    def test_list_respects_limit_query_param(self):
        for index in range(5):
            create_transaction(
                user=self.user,
                kind=Transaction.Kind.DEPOSIT,
                amount="1.00",
                description=f"seed {index}",
                destination_category=self.wallet,
            )

        response = self.client.get("/api/transactions/?limit=3")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)

    def test_withdraw_over_balance_returns_400_not_500(self):
        empty = make_category(self.user, "Transport", "transport", balance="0.00")

        response = self.client.post(
            "/api/transactions/",
            data={
                "kind": "withdraw",
                "amount": "250.00",
                "source_category": empty.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("amount", body)
        self.assertIn("Transport", body["amount"][0])
        self.assertIn("available", body["amount"][0])


class DashboardApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="rob", password="StrongPass123")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.wallet = make_category(self.user, "Wallet", "wallet", balance="0.00")
        self.food = make_category(self.user, "Food", "food", balance="0.00")

    def test_dashboard_aggregates_current_month_flow_and_totals(self):
        create_transaction(
            user=self.user,
            kind=Transaction.Kind.DEPOSIT,
            amount="200.00",
            destination_category=self.wallet,
        )
        create_transaction(
            user=self.user,
            kind=Transaction.Kind.WITHDRAW,
            amount="30.00",
            source_category=self.wallet,
            description="Lunch",
        )

        # Out-of-month transaction should not count toward monthly inflow/outflow.
        stale = create_transaction(
            user=self.user,
            kind=Transaction.Kind.DEPOSIT,
            amount="999.00",
            destination_category=self.food,
        )
        Transaction.objects.filter(pk=stale.pk).update(
            occurred_at=timezone.now().replace(day=1) - timedelta(days=40)
        )

        response = self.client.get("/api/dashboard/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(Decimal(payload["monthly_inflow"]), Decimal("200.00"))
        self.assertEqual(Decimal(payload["monthly_outflow"]), Decimal("30.00"))
        # Wallet: +200 -30 = 170, Food: +999 (historical)
        self.assertEqual(Decimal(payload["total_balance"]), Decimal("1169.00"))
        self.assertEqual(payload["category_count"], 2)


class RecurringRuleServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="rae", password="StrongPass123")
        self.wallet = make_category(self.user, "Wallet", "wallet", balance="2000.00")
        self.rent = make_category(self.user, "Rent", "rent", balance="0.00")

    def _make_rule(self, **overrides):
        defaults = {
            "user": self.user,
            "name": "Rent",
            "kind": Transaction.Kind.TRANSFER,
            "amount": Decimal("1200.00"),
            "description": "Monthly rent",
            "source_category": self.wallet,
            "destination_category": self.rent,
            "frequency": RecurringRule.Frequency.MONTHLY,
            "next_run_at": timezone.now() - timedelta(minutes=1),
            "is_active": True,
        }
        defaults.update(overrides)
        return RecurringRule.objects.create(**defaults)

    def test_advance_monthly_clamps_to_last_day_of_short_month(self):
        from datetime import datetime

        result = advance_next_run(
            timezone.make_aware(datetime(2026, 1, 31, 9, 0)),
            RecurringRule.Frequency.MONTHLY,
        )
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 28)

    def test_advance_weekly_adds_seven_days(self):
        from datetime import datetime

        result = advance_next_run(
            timezone.make_aware(datetime(2026, 5, 1, 9, 0)),
            RecurringRule.Frequency.WEEKLY,
        )
        self.assertEqual(result.day, 8)

    def test_advance_yearly_handles_leap_day(self):
        from datetime import datetime

        result = advance_next_run(
            timezone.make_aware(datetime(2024, 2, 29, 9, 0)),
            RecurringRule.Frequency.YEARLY,
        )
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.day, 28)

    def test_process_due_rule_creates_transaction_and_advances(self):
        rule = self._make_rule()

        created = process_due_recurring_rules(self.user)

        self.assertEqual(len(created), 1)
        self.wallet.refresh_from_db()
        self.rent.refresh_from_db()
        rule.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("800.00"))
        self.assertEqual(self.rent.balance, Decimal("1200.00"))
        self.assertGreater(rule.next_run_at, timezone.now())
        self.assertEqual(created[0].recurring_rule_id, rule.pk)
        self.assertEqual(rule.last_error, "")

    def test_process_skips_inactive_rule(self):
        self._make_rule(is_active=False)

        created = process_due_recurring_rules(self.user)

        self.assertEqual(created, [])
        self.assertEqual(Transaction.objects.count(), 0)

    def test_process_catches_up_multiple_missed_runs(self):
        # Three months overdue.
        rule = self._make_rule(
            amount=Decimal("100.00"),
            next_run_at=timezone.now() - timedelta(days=95),
        )

        created = process_due_recurring_rules(self.user)

        rule.refresh_from_db()
        self.assertGreaterEqual(len(created), 3)
        self.assertGreater(rule.next_run_at, timezone.now())

    def test_process_records_error_and_stops_when_funds_insufficient(self):
        rule = self._make_rule(
            kind=Transaction.Kind.WITHDRAW,
            source_category=self.rent,
            destination_category=None,
            amount=Decimal("9999.00"),
        )

        created = process_due_recurring_rules(self.user)

        rule.refresh_from_db()
        self.assertEqual(created, [])
        self.assertIn("available", rule.last_error)
        # next_run_at must NOT advance on failure — should retry next time.
        self.assertLess(rule.next_run_at, timezone.now())

    def test_process_deactivates_rule_past_end_date(self):
        rule = self._make_rule(
            amount=Decimal("50.00"),
            end_date=timezone.now().date() - timedelta(days=1),
            next_run_at=timezone.now() - timedelta(days=10),
        )

        process_due_recurring_rules(self.user)

        rule.refresh_from_db()
        self.assertFalse(rule.is_active)


class RecurringRuleApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mel", password="StrongPass123")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.wallet = make_category(self.user, "Wallet", "wallet", balance="500.00")
        self.utilities = make_category(self.user, "Utilities", "utilities", balance="0.00")

    def test_create_rule_returns_201_and_persists(self):
        payload = {
            "name": "Electric bill",
            "kind": "transfer",
            "amount": "75.00",
            "description": "Power",
            "source_category": self.wallet.pk,
            "destination_category": self.utilities.pk,
            "frequency": "monthly",
            "next_run_at": (timezone.now() + timedelta(days=3)).isoformat(),
        }

        response = self.client.post("/api/recurring-rules/", data=payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(RecurringRule.objects.count(), 1)

    def test_list_scoped_to_request_user(self):
        RecurringRule.objects.create(
            user=self.user,
            name="Mine",
            kind=Transaction.Kind.DEPOSIT,
            amount=Decimal("10.00"),
            destination_category=self.wallet,
            frequency=RecurringRule.Frequency.WEEKLY,
            next_run_at=timezone.now() + timedelta(days=1),
        )
        other = User.objects.create_user(username="other", password="StrongPass123")
        other_wallet = make_category(other, "Wallet", "wallet", balance="0.00")
        RecurringRule.objects.create(
            user=other,
            name="Theirs",
            kind=Transaction.Kind.DEPOSIT,
            amount=Decimal("10.00"),
            destination_category=other_wallet,
            frequency=RecurringRule.Frequency.WEEKLY,
            next_run_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.get("/api/recurring-rules/")

        self.assertEqual(response.status_code, 200)
        names = {item["name"] for item in response.json()}
        self.assertEqual(names, {"Mine"})

    def test_transactions_list_processes_due_rules(self):
        RecurringRule.objects.create(
            user=self.user,
            name="Auto-allocate",
            kind=Transaction.Kind.TRANSFER,
            amount=Decimal("25.00"),
            source_category=self.wallet,
            destination_category=self.utilities,
            frequency=RecurringRule.Frequency.WEEKLY,
            next_run_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.get("/api/transactions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.utilities.refresh_from_db()
        self.assertEqual(self.utilities.balance, Decimal("25.00"))

    def test_create_rejects_transfer_with_same_source_and_destination(self):
        payload = {
            "name": "Bad",
            "kind": "transfer",
            "amount": "10.00",
            "source_category": self.wallet.pk,
            "destination_category": self.wallet.pk,
            "frequency": "monthly",
            "next_run_at": (timezone.now() + timedelta(days=1)).isoformat(),
        }

        response = self.client.post("/api/recurring-rules/", data=payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("destination_category", response.json())
