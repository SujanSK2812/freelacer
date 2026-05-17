from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from projects.models import Job
from .forms import FreelancerProfileForm
from .models import Project, FreelancerProfile
import cloudinary.uploader
from django.http import HttpResponse
User = get_user_model()

@login_required
def freelancer_home(request):
    jobs = Job.objects.all().order_by("-created_at")

    for job in jobs:
        job.skills_list = job.skills.split(",")

    return render(request, "freelancer/home.html", {"jobs": jobs})


@login_required
def freelancer_dashboard(request):
    return render(request, "freelancer/dashboard.html")


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

@login_required
def create_profile(request):
    print("METHOD:", request.method)

    profile, created = FreelancerProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":
        print("POST HIT")

        profile.title = request.POST.get('title')
        profile.bio = request.POST.get('bio')
        profile.experience_level = request.POST.get('experience_level')
        profile.hourly_rate = request.POST.get('hourly_rate')
        profile.skills = request.POST.get('skills')
        profile.education = request.POST.get('education')
        profile.work_experience = request.POST.get('work_experience')
        profile.portfolio_link = request.POST.get('portfolio_link')
        profile.github_link = request.POST.get('github_link')
        profile.linkedin = request.POST.get('linkedin')
        profile.country = request.POST.get('country')
        profile.city = request.POST.get('city')

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
        return redirect("freelancer_dashboard")

    return render(request, "freelancer/edit_profile.html", {
        "user": user
    })



@login_required
def freelancer_profile(request, freelancer_id):

    freelancer = User.objects.get(id=freelancer_id)

    profile = FreelancerProfile.objects.filter(
        user=freelancer
    ).first()

    return render(
        request,
        "freelancer/freelancer_profile.html",
        {
            "freelancer": freelancer,
            "profile": profile
        }
    )