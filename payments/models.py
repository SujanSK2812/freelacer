from django.db import models
from django.conf import settings
from proposals.models import Proposal


class PaymentMethod(models.Model):
    METHOD_CHOICES = [
        ("card", "Credit / Debit Card"),
        ("upi", "UPI ID"),
        ("netbanking", "Net Banking"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_payment_methods"
    )
    method_type = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default="card"
    )
    card_holder_name = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )
    card_last4 = models.CharField(
        max_length=4,
        blank=True,
        default=""
    )
    card_brand = models.CharField(
        max_length=30,
        blank=True,
        default="Visa"
    )
    expiry_month = models.CharField(
        max_length=2,
        blank=True,
        default=""
    )
    expiry_year = models.CharField(
        max_length=4,
        blank=True,
        default=""
    )
    upi_id = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.method_type == "card":
            return f"{self.card_brand} ending in {self.card_last4}"
        elif self.method_type == "upi":
            return f"UPI ({self.upi_id})"
        return f"{self.bank_name} Net Banking"


class Payment(models.Model):
    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("pending", "Pending"),
        ("refunded", "Refunded"),
        ("failed", "Failed"),
    ]

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_payments"
    )

    freelancer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="freelancer_payments"
    )

    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=100,
        default="Credit / Debit Card"
    )

    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="completed"
    )

    razorpay_order_id = models.CharField(
        max_length=200,
        blank=True,
        default=""
    )

    razorpay_payment_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default=""
    )

    paid = models.BooleanField(default=False)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.client.username} paid ₹{self.amount} to {self.freelancer.username} (Status: {self.status})"