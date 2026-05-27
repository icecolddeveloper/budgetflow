from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.budget.models import Category, Transaction
from apps.budget.services import create_transaction


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
