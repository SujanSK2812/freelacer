from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from projects.models import Job



@login_required
def freelancer_home(request):

    jobs = Job.objects.all().order_by("-created_at")

    for job in jobs:
        job.skills_list = job.skills.split(",")

    return render(request, "freelancer/home.html", {"jobs": jobs})


@login_required
def freelancer_dashboard(request):
    return render(request,"freelancer/dashboard.html")



