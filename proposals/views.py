from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import freelancer_required
from django.contrib import messages

from .models import Proposal
from projects.models import Job


@freelancer_required
def submit_proposal(request, job_id):

    job = get_object_or_404(Job, id=job_id)

    # Check if job already has an accepted proposal (already awarded)
    if Proposal.objects.filter(job=job, status="accepted").exists():
        messages.error(request, "This job has already been awarded to a freelancer and is closed to new proposals.")
        return redirect("freelancer:freelancer_dashboard")

    # Prevent duplicate applications
    if Proposal.objects.filter(freelancer=request.user, job=job).exists():
        messages.error(request, "You have already applied for this job.")
        return redirect("freelancer:freelancer_dashboard")

    if request.method == "POST":

        proposal = Proposal.objects.create(
            freelancer=request.user,
            job=job,
            proposal_text=request.POST.get("proposal_text"),
            bid_amount=request.POST.get("bid_amount"),
            delivery_days=request.POST.get("delivery_days"),
        )
        
        from messages_app.models import Message
        
        # Create a message linked to the proposal
        Message.objects.create(
            sender=request.user,
            receiver=job.client,
            message="Submitted a new proposal.",
            proposal=proposal
        )
        
        from accounts.models import Notification
        from django.urls import reverse
        
        Notification.objects.create(
            user=job.client,
            notification_type='proposal_status',
            message=f"New proposal submitted by {request.user.username} on your job post <strong>{job.title}</strong>.",
            link=reverse("client:job_detail", args=[job.id])
        )

        return redirect("freelancer:my_proposals")

    return render(
        request,
        "proposals/submit_proposal.html",
        {"job": job}
    )


@freelancer_required
def my_proposals(request):

    proposals = Proposal.objects.filter(
        freelancer=request.user
    ).select_related('job', 'job__client').order_by("-created_at")

    from payments.models import Payment
    paid_map = {
        p.proposal_id: p
        for p in Payment.objects.filter(freelancer=request.user, paid=True)
    }
    for prop in proposals:
        prop.payment = paid_map.get(prop.id)
        prop.is_paid = prop.payment is not None

    return render(
        request,
        "proposals/my_proposals.html",
        {"proposals": proposals}
    )