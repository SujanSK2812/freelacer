from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import client_required
from projects.models import JobPost, Job
from django.contrib.auth import get_user_model

User = get_user_model()


@client_required
def client_home(request):
    if request.user.is_superuser:
        return redirect("accounts:admin_home")

    # Client Job Postings (Work available)
    client_jobs = Job.objects.select_related('client').filter(client__role='client').order_by("-created_at")
    for job in client_jobs:
        prof = getattr(job.client, 'freelancerprofile', None)
        job.author_dp = prof.profile_picture if (prof and prof.profile_picture) else None
        if hasattr(job, 'skills') and job.skills:
            job.skills_list = [s.strip() for s in job.skills.split(",") if s.strip()]
        else:
            job.skills_list = []

    # Freelancer Posts / Talent Showcases
    freelancer_posts = JobPost.objects.select_related('client').filter(client__role='freelancer').prefetch_related('comments__user', 'reactions').order_by("-created_at")

    for post in freelancer_posts:
        prof = getattr(post.client, 'freelancerprofile', None)
        post.author_dp = prof.profile_picture if (prof and prof.profile_picture) else None
        post.liked_by_user = post.reactions.filter(user=request.user, reaction_type='like').exists()
        post.likes_count = post.reactions.filter(reaction_type='like').count()
        post.comments_all = post.comments.all()
        for comment in post.comments_all:
            c_prof = getattr(comment.user, 'freelancerprofile', None)
            comment.author_dp = c_prof.profile_picture if (c_prof and c_prof.profile_picture) else None
        post.comments_count = post.comments_all.count()

    freelancers = User.objects.filter(role="freelancer")

    return render(request, "client/home.html", {
        "freelancers": freelancers,
        "jobs": client_jobs,
        "freelancer_posts": freelancer_posts,
    })


from proposals.models import Proposal

@client_required
def client_dashboard(request):
    client_jobs = Job.objects.filter(client=request.user).order_by('-created_at')
    
    active_jobs_count = client_jobs.count()
    proposals_count = Proposal.objects.filter(job__client=request.user).count()
    
    recommended_freelancers = User.objects.filter(role="freelancer")[:5]
    
    for job in client_jobs:
        job.proposal_count = Proposal.objects.filter(job=job).count()
        job.status = 'Open'  # Assuming all jobs are 'Open' for now

    recent_activities = Proposal.objects.filter(job__client=request.user).order_by('-created_at')[:5]

    return render(request, "client/dashboard.html", {
        "client_jobs": client_jobs,
        "active_jobs_count": active_jobs_count,
        "proposals_count": proposals_count,
        "recommended_freelancers": recommended_freelancers,
        "recent_activities": recent_activities,
    })

@client_required
def create_job(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        budget = request.POST.get("budget", "5000")
        skills = request.POST.get("skills", "Python, Web Development")
        experience_level = request.POST.get("experience_level", "Intermediate")
        image = request.FILES.get("image")

        Job.objects.create(
            client=request.user,
            title=title,
            description=description,
            budget=budget,
            skills=skills,
            experience_level=experience_level,
            image=image
        )
        messages.success(request, "Work posted successfully! Freelancers can now view it and submit proposals.")
        return redirect("/")

    return render(request, "client/create_job.html", {"is_client": True})


@client_required
def all_freelancers(request):

    freelancers = User.objects.filter(role="freelancer")

    return render(request, "client/all_freelancers.html", {
        "freelancers": freelancers
    })


@login_required
def job_detail(request, job_id):
    job = Job.objects.filter(id=job_id).first()
    if not job:
        job = get_object_or_404(JobPost, id=job_id)

    # Attach convenience attributes if it's a Job model instance
    if hasattr(job, 'experience_level') and not hasattr(job, 'experience_required'):
        setattr(job, 'experience_required', job.experience_level)
    if hasattr(job, 'skills') and not hasattr(job, 'category'):
        setattr(job, 'category', job.skills)

    return render(request, "client/job_detail.html", {
        "job": job
    })