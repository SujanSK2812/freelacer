from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from projects.models import Job
from .forms import FreelancerProfileForm
from .models import Project, FreelancerProfile
import cloudinary.uploader
from django.http import HttpResponse
User = get_user_model()
from accounts.models import Connection, ConnectionRequest
from django.shortcuts import get_object_or_404
from proposals.models import Proposal

def freelancer_home(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect("accounts:admin_home")

    # Client Job Postings (Work available)
    client_jobs = Job.objects.select_related('client').all().order_by("-created_at")
    for job in client_jobs:
        if hasattr(job, 'skills') and job.skills:
            job.skills_list = [s.strip() for s in job.skills.split(",") if s.strip()]
        else:
            job.skills_list = []

    # Freelancer Posts / Talent Showcases
    from projects.models import JobPost
    freelancer_posts = JobPost.objects.select_related('client').prefetch_related('comments__user', 'reactions').all().order_by("-created_at")

    for post in freelancer_posts:
        if request.user.is_authenticated:
            post.liked_by_user = post.reactions.filter(user=request.user, reaction_type='like').exists()
        else:
            post.liked_by_user = False
        post.likes_count = post.reactions.filter(reaction_type='like').count()
        post.comments_all = post.comments.all()
        post.comments_count = post.comments_all.count()

    profile = None
    proposals_count = 0
    if request.user.is_authenticated:
        profile = FreelancerProfile.objects.filter(user=request.user).first()
        proposals_count = Proposal.objects.filter(freelancer=request.user).count()

    context = {
        "jobs": client_jobs,
        "freelancer_posts": freelancer_posts,
        "profile": profile,
        "proposals_count": proposals_count,
    }

    return render(request, "freelancer/home.html", context)

from django.db.models import Sum
from payments.models import Payment

@login_required
def freelancer_dashboard(request):
    if request.user.is_superuser:
        return redirect("accounts:admin_home")

    freelancer_profile = FreelancerProfile.objects.filter(user=request.user).first()

    recent_proposals = Proposal.objects.filter(freelancer=request.user).order_by("-created_at")[:10]
    all_proposals = Proposal.objects.filter(freelancer=request.user)

    accepted_proposals = all_proposals.filter(status="accepted")
    pending_proposals = all_proposals.filter(status="pending")

    jobs = Job.objects.all().order_by("-created_at")[:6]
    for job in jobs:
        if hasattr(job, 'skills') and job.skills:
            job.skills_list = [s.strip() for s in job.skills.split(",") if s.strip()]
        else:
            job.skills_list = []

    skills_list = []
    if freelancer_profile and freelancer_profile.skills:
        skills_list = [s.strip() for s in freelancer_profile.skills.split(",") if s.strip()]

    # Calculate real total earnings from payments database table
    paid_payments = Payment.objects.filter(freelancer=request.user, paid=True)
    total_earnings = paid_payments.aggregate(total=Sum('amount'))['total'] or 0

    # Real profile completeness calculation
    profile_completeness = 20
    if freelancer_profile:
        if freelancer_profile.title: profile_completeness += 20
        if freelancer_profile.bio: profile_completeness += 20
        if freelancer_profile.skills: profile_completeness += 20
        if freelancer_profile.hourly_rate: profile_completeness += 20

    active_projects = Project.objects.filter(status='in_progress')

    context = {
        "recent_proposals": recent_proposals,
        "proposals_count": all_proposals.count(),
        "pending_proposals_count": pending_proposals.count(),
        "accepted_proposals_count": accepted_proposals.count(),
        "accepted_proposals": accepted_proposals,
        "total_earnings": total_earnings,
        "profile_completeness": profile_completeness,
        "freelancer": freelancer_profile,
        "skills_list": skills_list,
        "jobs": jobs,
        "active_projects": active_projects,
    }

    return render(
        request,
        "freelancer/dashboard.html",
        context
    )



@login_required
def search_results(request):
    query = request.GET.get('q')

    projects = []
    freelancers = []

    if query:
        projects = Project.objects.filter(title__icontains=query)

        freelancers = User.objects.filter(
            role="freelancer",
            username__icontains=query
        )

    return render(request, 'search_results.html', {
        'query': query,
        'projects': projects,
        'freelancers': freelancers
    })

from decimal import Decimal

@login_required
def create_profile(request):
    if request.user.is_superuser:
        return redirect("accounts:admin_home")

    print("METHOD:", request.method)

    profile, created = FreelancerProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":
        print("POST HIT")

        profile.title = request.POST.get('title')
        profile.bio = request.POST.get('bio')
        profile.experience_level = request.POST.get('experience_level')

        # FIX FOR DECIMAL ERROR
        hourly_rate = request.POST.get('hourly_rate')

        if hourly_rate and hourly_rate.strip():
            profile.hourly_rate = Decimal(hourly_rate)
        else:
            profile.hourly_rate = Decimal("0.00")

        profile.skills = request.POST.get('skills')
        profile.education = request.POST.get('education')
        profile.work_experience = request.POST.get('work_experience')
        profile.portfolio_link = request.POST.get('portfolio_link')
        profile.github_link = request.POST.get('github_link')
        profile.linkedin = request.POST.get('linkedin')
        profile.country = request.POST.get('country')
        profile.city = request.POST.get('city')

        # PROFILE IMAGE
        if request.FILES.get('profile_picture'):
            upload_result = cloudinary.uploader.upload(
                request.FILES['profile_picture']
            )

            profile.profile_picture = upload_result.get('secure_url')

        profile.save()

        print("SAVED SUCCESSFULLY")

        return redirect('/')

    return render(request, 'footers_file/create_profile.html', {
        'profile': profile
    })


@login_required
def my_proposals(request):
    # later you can fetch real proposals from DB
    proposals = []

    return render(request, "freelancer/my_proposals.html", {
        "proposals": proposals
    })



@login_required
def edit_profile(request):
    user = request.user

    if request.method == "POST":
        user.username = request.POST.get("username")
        user.save()
        return redirect("freelancer:freelancer_dashboard")

    return render(request, "freelancer/edit_profile.html", {
        "user": user
    })



@login_required
def freelancer_profile(request, freelancer_id):

    freelancer = get_object_or_404(User, id=freelancer_id)

    profile = FreelancerProfile.objects.filter(
        user=freelancer
    ).first()

    # pending requests
    requested_ids = ConnectionRequest.objects.filter(
        sender=request.user
    ).values_list("receiver_id", flat=True)

    # accepted/following
    connected_ids = Connection.objects.filter(
        sender=request.user
    ).values_list("receiver_id", flat=True)

    context = {
        "freelancer": freelancer,
        "profile": profile,
        "requested_ids": requested_ids,
        "connected_ids": connected_ids,
    }

    return render(
        request,
        "freelancer/freelancer_profile.html",
        context
    )



@login_required
def freelancer_connections(request):

    sent_connections = Connection.objects.filter(
        sender=request.user
    )

    received_connections = Connection.objects.filter(
        receiver=request.user
    )

    connected_users = []

    for connection in sent_connections:
        connected_users.append(connection.receiver)

    for connection in received_connections:
        connected_users.append(connection.sender)

    return render(
        request,
        'freelancer/connections.html',
        {
            'connected_users': connected_users
        }
    )




# {% if profile.profile_picture %}
#     <img src="{{ profile.profile_picture }}" alt="Profile">
# {% endif %}