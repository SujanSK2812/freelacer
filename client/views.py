from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from projects.models import JobPost
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def client_home(request):

    freelancers = User.objects.filter(role="freelancer")

    posts = JobPost.objects.filter(
        client=request.user
    ).order_by("-created_at")

    return render(request, "client/home.html", {
    "freelancers": freelancers,
    "jobs": posts
})


@login_required
def client_dashboard(request):
    return render(request, "client/dashboard.html")


@login_required
def create_job(request):

    if request.method == "POST":

        title = request.POST.get("title")
        description = request.POST.get("description")
        image = request.FILES.get("image")

        JobPost.objects.create(
            client=request.user,
            title=title,
            description=description,
            image=image
        )

        return redirect("client:client_home")

    return render(request, "client/create_job.html")


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