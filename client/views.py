from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from projects.models import JobPost, Job
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def client_home(request):

    # Client Job Postings (Work available)
    client_jobs = Job.objects.select_related('client').all().order_by("-created_at")
    for job in client_jobs:
        if hasattr(job, 'skills') and job.skills:
            job.skills_list = [s.strip() for s in job.skills.split(",") if s.strip()]
        else:
            job.skills_list = []

    # Freelancer Posts / Talent Showcases
    freelancer_posts = JobPost.objects.select_related('client').prefetch_related('comments__user', 'reactions').all().order_by("-created_at")

    for post in freelancer_posts:
        post.liked_by_user = post.reactions.filter(user=request.user, reaction_type='like').exists()
        post.likes_count = post.reactions.filter(reaction_type='like').count()
        post.comments_all = post.comments.all()
        post.comments_count = post.comments_all.count()

    freelancers = User.objects.filter(role="freelancer")

    return render(request, "freelancer/home.html", {
        "freelancers": freelancers,
        "jobs": client_jobs,
        "freelancer_posts": freelancer_posts,
    })


@login_required
def client_dashboard(request):
    return render(request, "client/dashboard.html")


@login_required
def create_job(request):

    is_client = getattr(request.user, 'role', None) == 'client' or request.user.is_superuser

    if request.method == "POST":

        title = request.POST.get("title")
        description = request.POST.get("description")
        budget = request.POST.get("budget", "5000")
        skills = request.POST.get("skills", "Python, Web Development")
        experience_level = request.POST.get("experience_level", "Intermediate")
        image = request.FILES.get("image")

        if is_client:
            Job.objects.create(
                client=request.user,
                title=title,
                description=description,
                budget=budget,
                skills=skills,
                experience_level=experience_level
            )
            messages.success(request, "Work posted successfully! Freelancers can now view it and submit proposals.")
        else:
            messages.success(request, "Talent showcase posted successfully! Clients can now view your skills.")

        JobPost.objects.create(
            client=request.user,
            title=title,
            description=description,
            image=image
        )

        return redirect("/")

    return render(request, "client/create_job.html", {"is_client": is_client})


@login_required
def all_freelancers(request):

    freelancers = User.objects.filter(role="freelancer")

    return render(request, "client/all_freelancers.html", {
        "freelancers": freelancers
    })


@login_required
def job_detail(request, job_id):

    job = get_object_or_404(JobPost, id=job_id)

    return render(request, "client/job_detail.html", {
        "job": job
    })