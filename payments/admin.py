from django.contrib import admin
from .models import Payment, PaymentMethod, FreelancerPayoutDetail, ContractorPayoutTransaction


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "client", "freelancer", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("transaction_id", "client__username", "freelancer__username")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("user", "method_type", "is_default", "created_at")
    list_filter = ("method_type", "is_default")
    search_fields = ("user__username", "upi_id", "card_holder_name")


@admin.register(FreelancerPayoutDetail)
class FreelancerPayoutDetailAdmin(admin.ModelAdmin):
    list_display = ("freelancer", "account_holder_name", "preferred_method", "upi_id", "bank_name", "is_verified", "updated_at")
    list_filter = ("preferred_method", "is_verified")
    search_fields = ("freelancer__username", "account_holder_name", "upi_id", "account_number")


@admin.register(ContractorPayoutTransaction)
class ContractorPayoutTransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "freelancer", "amount", "payout_method", "status", "created_at")
    list_filter = ("status", "payout_method", "created_at")
    search_fields = ("transaction_id", "freelancer__username", "project_title", "recipient_detail")
