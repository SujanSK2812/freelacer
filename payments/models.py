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


class FreelancerPayoutDetail(models.Model):
    """
    Stores beneficiary payment details for a contractor/freelancer.
    """
    PAYOUT_METHOD_CHOICES = [
        ("upi", "UPI / Virtual Payment Address"),
        ("bank", "Bank Account (NEFT / IMPS)"),
    ]

    freelancer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payout_profile"
    )
    account_holder_name = models.CharField(max_length=150)
    preferred_method = models.CharField(max_length=20, choices=PAYOUT_METHOD_CHOICES, default="upi")
    
    # UPI Details
    upi_id = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. name@okhdfcbank")
    
    # Bank Account Details
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=25, blank=True, null=True)
    
    is_verified = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def masked_account_number(self):
        if self.account_number and len(self.account_number) > 4:
            return f"•••• •••• {self.account_number[-4:]}"
        return self.account_number or ""

    def get_display_recipient(self):
        if self.preferred_method == "upi" and self.upi_id:
            return f"UPI ({self.upi_id})"
        elif self.preferred_method == "bank" and self.bank_name:
            return f"{self.bank_name} ({self.masked_account_number})"
        return "Account Details Not Set"

    def __str__(self):
        return f"{self.freelancer.username} - {self.get_preferred_method_display()}"


class ContractorPayoutTransaction(models.Model):
    """
    Records an individual contractor payout initiated by an admin.
    """
    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("processing", "Processing"),
        ("pending", "Pending"),
        ("failed", "Failed"),
    ]

    METHOD_CHOICES = [
        ("upi", "UPI Transfer"),
        ("bank", "Bank Transfer (NEFT/IMPS)"),
    ]

    transaction_id = models.CharField(max_length=64, unique=True, db_index=True)
    freelancer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contractor_payouts"
    )
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiated_payouts"
    )
    job = models.ForeignKey(
        "projects.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contractor_payouts"
    )
    project_title = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payout_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="upi")
    recipient_detail = models.CharField(
        max_length=255,
        help_text="Snapshot of the UPI ID or masked bank account used at time of payout"
    )
    account_holder_name = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_id} - ₹{self.amount} to {self.freelancer.username} ({self.status})"