from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import Proposal
from projects.models import Job


@login_required
def submit_proposal(request, job_id):

    job = get_object_or_404(Job, id=job_id)

    if request.method == "POST":

        Proposal.objects.create(
            freelancer=request.user,
            job=job,
            proposal_text=request.POST.get("proposal_text"),
            bid_amount=request.POST.get("bid_amount"),
            delivery_days=request.POST.get("delivery_days"),
        )

        return redirect("my_proposals")

    return render(
        request,
        "proposals/submit_proposal.html",
        {"job": job}
    )


@login_required
def my_proposals(request):

    proposals = Proposal.objects.filter(
        freelancer=request.user
    ).order_by("-created_at")

    return render(
        request,
        "proposals/my_proposals.html",
        {"proposals": proposals}
    )