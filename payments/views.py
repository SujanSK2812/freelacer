import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.core.exceptions import PermissionDenied

from accounts.models import Notification
from proposals.models import Proposal
from .models import Payment, PaymentMethod


def detect_card_brand(card_number):
    cleaned = card_number.replace(" ", "").replace("-", "")
    if cleaned.startswith("4"):
        return "Visa"
    elif cleaned.startswith(("51", "52", "53", "54", "55", "22", "23", "24", "25", "26", "27")):
        return "Mastercard"
    elif cleaned.startswith(("60", "65", "81", "82")):
        return "RuPay"
    elif cleaned.startswith(("34", "37")):
        return "American Express"
    return "Card"


@login_required
def payment_methods_view(request):
    if hasattr(request.user, 'role') and request.user.role == 'freelancer':
        messages.info(request, "Payment methods management is for client accounts.")
        return redirect('freelancer:freelancer_dashboard')

    saved_methods = PaymentMethod.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    payments_history = Payment.objects.filter(
        client=request.user,
        paid=True
    ).select_related('freelancer', 'proposal', 'proposal__job').order_by('-created_at')

    return render(request, "payments/payment_methods.html", {
        "saved_methods": saved_methods,
        "payments_history": payments_history,
    })


@login_required
def add_payment_method(request):
    if request.method == "POST":
        method_type = request.POST.get("method_type", "card")
        is_default = request.POST.get("is_default") == "on"

        if is_default:
            PaymentMethod.objects.filter(user=request.user).update(is_default=False)

        # Check if first method
        if not PaymentMethod.objects.filter(user=request.user).exists():
            is_default = True

        if method_type == "card":
            card_number = request.POST.get("card_number", "").strip().replace(" ", "").replace("-", "")
            card_holder_name = request.POST.get("card_holder_name", "").strip()
            expiry_month = request.POST.get("expiry_month", "").strip()
            expiry_year = request.POST.get("expiry_year", "").strip()

            if not card_number or len(card_number) < 4:
                messages.error(request, "Please enter a valid card number.")
                return redirect("payments:payment_methods")

            card_last4 = card_number[-4:]
            card_brand = detect_card_brand(card_number)

            PaymentMethod.objects.create(
                user=request.user,
                method_type="card",
                card_holder_name=card_holder_name or request.user.get_full_name() or request.user.username,
                card_last4=card_last4,
                card_brand=card_brand,
                expiry_month=expiry_month,
                expiry_year=expiry_year,
                is_default=is_default,
            )
            messages.success(request, f"{card_brand} card ending in {card_last4} added successfully!")

        elif method_type == "upi":
            upi_id = request.POST.get("upi_id", "").strip()
            if not upi_id or "@" not in upi_id:
                messages.error(request, "Please enter a valid UPI ID (e.g. yourname@okhdfcbank).")
                return redirect("payments:payment_methods")

            PaymentMethod.objects.create(
                user=request.user,
                method_type="upi",
                upi_id=upi_id,
                is_default=is_default,
            )
            messages.success(request, f"UPI ID '{upi_id}' saved successfully!")

        elif method_type == "netbanking":
            bank_name = request.POST.get("bank_name", "Primary Bank").strip()
            PaymentMethod.objects.create(
                user=request.user,
                method_type="netbanking",
                bank_name=bank_name,
                is_default=is_default,
            )
            messages.success(request, f"{bank_name} added to your payment methods!")

    return redirect("payments:payment_methods")


@login_required
def delete_payment_method(request, method_id):
    if request.method == "POST":
        method = get_object_or_404(PaymentMethod, id=method_id, user=request.user)
        name = str(method)
        was_default = method.is_default
        method.delete()

        # If deleted method was default, set next available method as default
        if was_default:
            next_method = PaymentMethod.objects.filter(user=request.user).first()
            if next_method:
                next_method.is_default = True
                next_method.save()

        messages.success(request, f"Removed {name} from your payment methods.")
    return redirect("payments:payment_methods")


@login_required
def checkout_view(request, proposal_id):
    proposal = get_object_or_404(
        Proposal.objects.select_related("job", "job__client", "freelancer"),
        id=proposal_id
    )

    # Only the job's client can pay
    if proposal.job.client != request.user and not request.user.is_superuser:
        raise PermissionDenied("You do not have permission to make payments for this job.")

    # Must be accepted
    if proposal.status != "accepted":
        messages.warning(request, "This proposal must be accepted first before making payment.")
        return redirect("client:client_proposals")

    # Check if already paid
    existing_payment = Payment.objects.filter(proposal=proposal, paid=True).first()
    if existing_payment:
        messages.info(request, "Payment for this proposal has already been completed.")
        return redirect("payments:payment_receipt", payment_id=existing_payment.id)

    saved_methods = PaymentMethod.objects.filter(user=request.user).order_by("-is_default", "-created_at")

    if request.method == "POST":
        payment_source = request.POST.get("payment_source", "card")
        payment_method_display = "Credit / Debit Card"

        if payment_source == "saved":
            saved_id = request.POST.get("saved_method_id")
            if saved_id:
                try:
                    sm = PaymentMethod.objects.get(id=saved_id, user=request.user)
                    payment_method_display = str(sm)
                except PaymentMethod.DoesNotExist:
                    payment_method_display = "Saved Payment Method"
        elif payment_source == "new_card":
            card_num = request.POST.get("card_number", "").strip().replace(" ", "").replace("-", "")
            card_last4 = card_num[-4:] if len(card_num) >= 4 else "1234"
            brand = detect_card_brand(card_num)
            payment_method_display = f"{brand} ending in {card_last4}"

            if request.POST.get("save_card") == "on":
                PaymentMethod.objects.create(
                    user=request.user,
                    method_type="card",
                    card_holder_name=request.POST.get("card_holder_name", "").strip() or request.user.get_full_name() or request.user.username,
                    card_last4=card_last4,
                    card_brand=brand,
                    expiry_month=request.POST.get("expiry_month", "").strip(),
                    expiry_year=request.POST.get("expiry_year", "").strip(),
                    is_default=not saved_methods.exists(),
                )
        elif payment_source == "upi":
            upi_id = request.POST.get("upi_id", "").strip()
            payment_method_display = f"UPI ({upi_id})" if upi_id else "UPI Payment"
            if request.POST.get("save_upi") == "on" and upi_id:
                PaymentMethod.objects.create(
                    user=request.user,
                    method_type="upi",
                    upi_id=upi_id,
                    is_default=not saved_methods.exists(),
                )
        elif payment_source == "netbanking":
            bank_name = request.POST.get("bank_name", "Primary Bank")
            payment_method_display = f"{bank_name} Net Banking"

        txn_id = "TXN-" + uuid.uuid4().hex[:12].upper()

        payment = Payment.objects.create(
            client=request.user,
            freelancer=proposal.freelancer,
            proposal=proposal,
            amount=proposal.bid_amount,
            payment_method=payment_method_display,
            transaction_id=txn_id,
            status="completed",
            paid=True,
            razorpay_order_id=f"ORD-{txn_id[4:12]}",
            razorpay_payment_id=f"PAY-{txn_id[4:12]}",
        )

        # Notify Freelancer
        Notification.objects.create(
            user=proposal.freelancer,
            notification_type="proposal_status",
            message=f"💰 Client <strong>{request.user.username}</strong> has completed payment of <strong>₹{proposal.bid_amount}</strong> for job <strong>{proposal.job.title}</strong>! You can now start working on the deliverables.",
            link=reverse("freelancer:my_proposals"),
        )

        # Notify Client
        Notification.objects.create(
            user=request.user,
            notification_type="proposal_status",
            message=f"✅ Payment of <strong>₹{proposal.bid_amount}</strong> for job <strong>{proposal.job.title}</strong> was successful. (Transaction ID: {txn_id}).",
            link=reverse("payments:payment_receipt", kwargs={"payment_id": payment.id}),
        )

        messages.success(
            request,
            f"🎉 Payment of ₹{proposal.bid_amount} completed successfully! Contract is funded and freelancer has been notified."
        )
        return redirect("payments:payment_receipt", payment_id=payment.id)

    return render(request, "payments/checkout.html", {
        "proposal": proposal,
        "saved_methods": saved_methods,
    })


@login_required
def payment_receipt_view(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related("client", "freelancer", "proposal", "proposal__job"),
        id=payment_id
    )

    if request.user != payment.client and request.user != payment.freelancer and not request.user.is_staff:
        raise PermissionDenied("You do not have permission to view this receipt.")

    return render(request, "payments/receipt.html", {
        "payment": payment,
        "is_payer": request.user == payment.client,
    })


@login_required
def freelancer_payment_history_view(request):
    from django.db.models import Sum

    payments = Payment.objects.filter(
        freelancer=request.user,
        paid=True
    ).select_related("client", "proposal", "proposal__job").order_by("-created_at")

    total_earnings = payments.aggregate(total=Sum("amount"))["total"] or 0

    return render(request, "payments/freelancer_history.html", {
        "payments": payments,
        "total_earnings": total_earnings,
        "total_payments_count": payments.count(),
    })

