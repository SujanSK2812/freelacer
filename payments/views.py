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
    freelancer_payout = getattr(proposal.freelancer, "payout_profile", None)

    if request.method == "POST":
        payment_source = request.POST.get("payment_source", "freelancer_account" if freelancer_payout else "card")
        payment_method_display = "Credit / Debit Card"

        if payment_source in ["freelancer_account", "freelancer_upi", "freelancer_bank"]:
            if freelancer_payout:
                if freelancer_payout.preferred_method == "upi" and freelancer_payout.upi_id:
                    payment_method_display = f"UPI ({freelancer_payout.upi_id})"
                elif freelancer_payout.preferred_method == "bank" and freelancer_payout.bank_name:
                    ac_suffix = freelancer_payout.account_number[-4:] if freelancer_payout.account_number else "A/C"
                    payment_method_display = f"Bank Transfer ({freelancer_payout.bank_name} - {ac_suffix})"
                else:
                    payment_method_display = f"Direct Transfer ({freelancer_payout.account_holder_name})"
            else:
                payment_method_display = "Direct Freelancer Payout"

        elif payment_source == "saved":
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
            if not upi_id and freelancer_payout and freelancer_payout.preferred_method == "upi" and freelancer_payout.upi_id:
                upi_id = freelancer_payout.upi_id
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
        "freelancer_payout": freelancer_payout,
    })


@login_required
def payment_receipt_view(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related("client", "freelancer", "proposal", "proposal__job"),
        id=payment_id
    )

    if request.user != payment.client and request.user != payment.freelancer and not request.user.is_staff:
        raise PermissionDenied("You do not have permission to view this receipt.")

    freelancer_payout = getattr(payment.freelancer, "payout_profile", None)

    return render(request, "payments/receipt.html", {
        "payment": payment,
        "is_payer": request.user == payment.client,
        "freelancer_payout": freelancer_payout,
    })


@login_required
def freelancer_payment_history_view(request):
    from django.db.models import Sum

    if request.method == "POST":
        action = request.POST.get("action", "save_payout_detail")
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.POST.get("ajax") == "1"

        if action == "save_payout_detail":
            account_holder_name = request.POST.get("account_holder_name", "").strip()
            preferred_method = request.POST.get("preferred_method", "upi").strip().lower()
            upi_id = request.POST.get("upi_id", "").strip()
            bank_name = request.POST.get("bank_name", "").strip()
            account_number = request.POST.get("account_number", "").strip()
            ifsc_code = request.POST.get("ifsc_code", "").strip().upper()

            if not account_holder_name:
                err = "Account holder name is required."
                if is_ajax:
                    return JsonResponse({"success": False, "error": err}, status=400)
                messages.error(request, err)
                return redirect("payments:freelancer_payment_history")

            if preferred_method == "upi":
                if not upi_id or "@" not in upi_id:
                    err = "Please enter a valid UPI ID (e.g. name@okhdfcbank or 9148937633@paytm)."
                    if is_ajax:
                        return JsonResponse({"success": False, "error": err}, status=400)
                    messages.error(request, err)
                    return redirect("payments:freelancer_payment_history")
            elif preferred_method == "bank":
                if not bank_name or not account_number or not ifsc_code:
                    err = "Bank Name, Account Number, and IFSC Code are required for bank transfer."
                    if is_ajax:
                        return JsonResponse({"success": False, "error": err}, status=400)
                    messages.error(request, err)
                    return redirect("payments:freelancer_payment_history")

            payout_detail, created = FreelancerPayoutDetail.objects.update_or_create(
                freelancer=request.user,
                defaults={
                    "account_holder_name": account_holder_name,
                    "preferred_method": preferred_method,
                    "upi_id": upi_id if preferred_method == "upi" else (upi_id or None),
                    "bank_name": bank_name if preferred_method == "bank" else (bank_name or None),
                    "account_number": account_number if preferred_method == "bank" else (account_number or None),
                    "ifsc_code": ifsc_code if preferred_method == "bank" else (ifsc_code or None),
                    "is_verified": True,
                }
            )

            msg = "Payment receiving account details saved successfully! Clients will make payments to this account."
            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "message": msg,
                    "preferred_method": payout_detail.preferred_method,
                    "account_holder_name": payout_detail.account_holder_name,
                    "display": payout_detail.get_display_recipient(),
                })
            messages.success(request, msg)
            return redirect("payments:freelancer_payment_history")

    payments = Payment.objects.filter(
        freelancer=request.user,
        paid=True
    ).select_related("client", "proposal", "proposal__job").order_by("-created_at")

    total_earnings = payments.aggregate(total=Sum("amount"))["total"] or 0
    payout_detail = getattr(request.user, "payout_profile", None)

    return render(request, "payments/freelancer_history.html", {
        "payments": payments,
        "total_earnings": total_earnings,
        "total_payments_count": payments.count(),
        "payout_detail": payout_detail,
    })


from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils import timezone
from projects.models import Job
from .models import FreelancerPayoutDetail, ContractorPayoutTransaction
from decimal import Decimal, InvalidOperation

User = get_user_model()


@login_required
def admin_contractor_payout_view(request):
    """
    Admin interface to initiate payouts to contractors/freelancers and view payout history.
    """
    if request.method == "POST":
        freelancer_id = request.POST.get("freelancer_id")
        project_title = request.POST.get("project_title", "").strip()
        job_id = request.POST.get("job_id")
        amount_raw = request.POST.get("amount", "0").strip()
        payout_method = request.POST.get("payout_method", "upi")
        account_holder_name = request.POST.get("account_holder_name", "").strip()
        upi_id = request.POST.get("upi_id", "").strip()
        bank_name = request.POST.get("bank_name", "").strip()
        account_number = request.POST.get("account_number", "").strip()
        ifsc_code = request.POST.get("ifsc_code", "").strip()
        notes = request.POST.get("notes", "").strip()
        status = request.POST.get("status", "completed")

        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.POST.get("ajax") == "1"

        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")
        except (InvalidOperation, ValueError) as e:
            if is_ajax:
                return JsonResponse({"success": False, "error": str(e)}, status=400)
            messages.error(request, f"Invalid payout amount: {e}")
            return redirect("payments:admin_contractor_payouts")

        freelancer = get_object_or_404(User, id=freelancer_id)

        job_instance = None
        if job_id and job_id.isdigit():
            job_instance = Job.objects.filter(id=int(job_id)).first()
            if job_instance and not project_title:
                project_title = job_instance.title

        if not project_title:
            project_title = "General Contractor Milestone"

        if not account_holder_name:
            account_holder_name = freelancer.get_full_name() or freelancer.username

        # Format recipient detail snapshot
        if payout_method == "upi":
            recipient_detail = f"UPI: {upi_id} ({account_holder_name})"
        else:
            masked_acc = f"••••{account_number[-4:]}" if len(account_number) >= 4 else account_number
            recipient_detail = f"{bank_name} A/C {masked_acc} (IFSC: {ifsc_code})"

        # Generate unique transaction ID
        unique_suffix = uuid.uuid4().hex[:8].upper()
        transaction_id = f"TXN-PO-{timezone.now().strftime('%Y%m%d')}-{unique_suffix}"

        # Save or update freelancer's payout profile for future payouts
        payout_detail, _ = FreelancerPayoutDetail.objects.get_or_create(freelancer=freelancer)
        payout_detail.account_holder_name = account_holder_name
        payout_detail.preferred_method = payout_method
        if payout_method == "upi" and upi_id:
            payout_detail.upi_id = upi_id
        elif payout_method == "bank":
            if bank_name:
                payout_detail.bank_name = bank_name
            if account_number:
                payout_detail.account_number = account_number
            if ifsc_code:
                payout_detail.ifsc_code = ifsc_code
        payout_detail.save()

        # Create ContractorPayoutTransaction
        payout_txn = ContractorPayoutTransaction.objects.create(
            transaction_id=transaction_id,
            freelancer=freelancer,
            admin_user=request.user,
            job=job_instance,
            project_title=project_title,
            amount=amount,
            payout_method=payout_method,
            recipient_detail=recipient_detail,
            account_holder_name=account_holder_name,
            status=status,
            notes=notes,
            completed_at=timezone.now() if status == "completed" else None,
        )

        # Notify the freelancer
        try:
            Notification.objects.create(
                user=freelancer,
                title="Payout Initiated",
                message=f"An admin payout of ₹{amount:,.2f} for project '{project_title}' has been successfully processed. Transaction Ref: {transaction_id}."
            )
        except Exception:
            pass

        if is_ajax:
            return JsonResponse({
                "success": True,
                "transaction_id": transaction_id,
                "amount": str(amount),
                "recipient": recipient_detail,
                "freelancer": freelancer.username,
                "status": status,
                "message": f"Payout of ₹{amount:,.2f} successfully recorded with ID {transaction_id}!"
            })

        messages.success(request, f"Payout of ₹{amount:,.2f} to {freelancer.username} was initiated successfully! Reference: {transaction_id}")
        return redirect("payments:admin_contractor_payouts")

    # GET Request: Prepare history table, stats, and form choices
    freelancers = User.objects.filter(role="freelancer").select_related("freelancerprofile").order_by("username")
    recent_jobs = Job.objects.all().order_by("-created_at")[:40]

    payouts = ContractorPayoutTransaction.objects.select_related("freelancer", "job", "admin_user").order_by("-created_at")

    from django.db.models import Sum, Count
    total_paid_out = payouts.filter(status="completed").aggregate(Sum("amount"))["amount__sum"] or 0
    total_payout_count = payouts.count()
    active_contractors_count = payouts.values("freelancer").distinct().count()

    return render(request, "payments/contractor_payouts.html", {
        "freelancers": freelancers,
        "recent_jobs": recent_jobs,
        "payouts": payouts,
        "total_paid_out": total_paid_out,
        "total_payout_count": total_payout_count,
        "active_contractors_count": active_contractors_count,
    })


@login_required
def freelancer_payout_info_api(request, freelancer_id):
    """
    API endpoint returning saved payout profile and recent proposals/jobs for a selected freelancer.
    """
    freelancer = get_object_or_404(User, id=freelancer_id)
    payout_detail = getattr(freelancer, "payout_profile", None)

    # Fetch accepted or recent proposals/jobs for this freelancer
    proposals = Proposal.objects.filter(freelancer=freelancer).select_related("job").order_by("-created_at")[:10]
    jobs_data = []
    for p in proposals:
        if p.job:
            jobs_data.append({
                "job_id": p.job.id,
                "title": p.job.title,
                "client": p.job.client.username if hasattr(p.job, "client") and p.job.client else "",
                "bid_amount": str(p.bid_amount),
                "status": p.status,
            })

    data = {
        "success": True,
        "freelancer_id": freelancer.id,
        "username": freelancer.username,
        "full_name": freelancer.get_full_name() or freelancer.username,
        "has_payout_profile": payout_detail is not None,
        "has_profile": payout_detail is not None,
        "account_holder_name": payout_detail.account_holder_name if payout_detail else (freelancer.get_full_name() or freelancer.username),
        "preferred_method": payout_detail.preferred_method if payout_detail else "upi",
        "upi_id": payout_detail.upi_id if payout_detail and payout_detail.upi_id else "",
        "bank_name": payout_detail.bank_name if payout_detail and payout_detail.bank_name else "",
        "account_number": payout_detail.account_number if payout_detail and payout_detail.account_number else "",
        "ifsc_code": payout_detail.ifsc_code if payout_detail and payout_detail.ifsc_code else "",
        "jobs": jobs_data,
    }
    return JsonResponse(data)


@login_required
def contractor_payout_receipt_view(request, transaction_id):
    """
    Detailed official receipt view for a contractor payout transaction.
    """
    payout = get_object_or_404(
        ContractorPayoutTransaction.objects.select_related("freelancer", "job", "admin_user"),
        transaction_id=transaction_id
    )

    if request.user != payout.freelancer and not request.user.is_staff and request.user != payout.admin_user:
        raise PermissionDenied("You do not have permission to view this payout receipt.")

    return render(request, "payments/payout_receipt.html", {
        "payout": payout,
    })


@login_required
def delete_contractor_payout(request, payout_id):
    """
    Deletes a contractor payout transaction record.
    """
    if request.method == "POST":
        payout = get_object_or_404(ContractorPayoutTransaction, id=payout_id)
        
        # Check permissions: staff, superuser, client or the admin who initiated
        if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'role', '') == 'client' or request.user == payout.admin_user):
            raise PermissionDenied("You do not have permission to delete this payout record.")
        
        txn_id = payout.transaction_id
        freelancer_name = payout.freelancer.get_full_name() or payout.freelancer.username
        amount = payout.amount
        payout.delete()

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "message": f"Payout record {txn_id} (₹{amount}) deleted successfully."
            })

        messages.success(request, f"Payout record {txn_id} for {freelancer_name} was deleted successfully.")
    
        referer = request.META.get("HTTP_REFERER")
        if referer:
            return redirect(referer)
        return redirect("payments:admin_contractor_payouts")
    
    return redirect("payments:admin_contractor_payouts")


contractor_payout_view = admin_contractor_payout_view



