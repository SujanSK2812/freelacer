from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import freelancer_required
from django.contrib import messages

from .models import Proposal
from projects.models import Job


@freelancer_required
def submit_proposal(request, job_id):

    job = get_object_or_404(Job, id=job_id)

    # Prevent duplicate applications
    if Proposal.objects.filter(freelancer=request.user, job=job).exists():
        messages.error(request, "You have already applied for this job.")
        return redirect("freelancer:freelancer_dashboard")

    if request.method == "POST":

        Proposal.objects.create(
            freelancer=request.user,
            job=job,
            proposal_text=request.POST.get("proposal_text"),
            bid_amount=request.POST.get("bid_amount"),
            delivery_days=request.POST.get("delivery_days"),
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
    ).order_by("-created_at")

    return render(
        request,
        "proposals/my_proposals.html",
        {"proposals": proposals}
    )