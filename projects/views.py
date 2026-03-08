# from django.shortcuts import render,redirect
# from .models import Job
# from django.shortcuts import render, get_object_or_404
# from .models import JobPost,JobLike,JobComment
# from django.shortcuts import render,redirect,get_object_or_404
# from .models import JobPost,Reaction,Comment
# def freelancer_home(request):
#     jobs = Job.objects.all().order_by('-created_at')
#     return render(request,'freelancer/home.html',{'jobs':jobs})


# def job_detail(request, id):
#     job = get_object_or_404(Job, id=id)
#     return render(request, "projects/job_detail.html", {"job": job})


# def job_feed(request):

#     jobs = JobPost.objects.all().order_by("-created_at")

#     return render(request,"projects/job_feed.html",{"jobs":jobs})


# def create_job(request):

#     if request.method == "POST":

#         title = request.POST.get("title")
#         description = request.POST.get("description")
#         image = request.FILES.get("image")

#         JobPost.objects.create(
#             client=request.user,
#             title=title,
#             description=description,
#             image=image
#         )

#         return redirect("job_feed")

#     return render(request,"projects/create_job.html")


# def like_job(request,id):

#     job = get_object_or_404(JobPost,id=id)

#     like,created = JobLike.objects.get_or_create(user=request.user,job=job)

#     if not created:
#         like.delete()

#     return redirect("job_feed")


# def post_job(request):

#     if request.method == "POST":

#         title = request.POST.get("title")
#         description = request.POST.get("description")
#         budget = request.POST.get("budget")
#         skills = request.POST.get("skills")
#         experience = request.POST.get("experience")

#         Job.objects.create(
#             client=request.user,
#             title=title,
#             description=description,
#             budget=budget,
#             skills=skills,
#             experience_level=experience
#         )

#         return redirect("client_dashboard")

#     return render(request,"projects/post_job.html")


# def client_home(request):

#     jobs = JobPost.objects.all().order_by("-created_at")

#     return render(request,"client/client_home.html",{"jobs":jobs})




# def react_job(request,id,reaction):

#     job = get_object_or_404(JobPost,id=id)

#     Reaction.objects.update_or_create(
#         user=request.user,
#         job=job,
#         defaults={"reaction_type":reaction}
#     )

#     return redirect("client_home")


# def comment_job(request,id):




#     job = get_object_or_404(JobPost,id=id)

#     if request.method == "POST":

#         text = request.POST.get("comment")

#         Comment.objects.create(
#             user=request.user,
#             job=job,
#             text=text
#         )

#     return redirect("client_home")

from django.shortcuts import render, redirect, get_object_or_404
from .models import Job, JobPost, Reaction, Comment


# ===============================
# Freelancer Home (Job Listing)
# ===============================

def freelancer_home(request):

    jobs = Job.objects.all().order_by("-created_at")

    return render(request, "freelancer/home.html", {"jobs": jobs})


# ===============================
# Job Detail
# ===============================

def job_detail(request, id):

    job = get_object_or_404(Job, id=id)

    return render(request, "projects/job_detail.html", {"job": job})


# ===============================
# Client Job Feed
# ===============================

def client_home(request):

    jobs = JobPost.objects.all().order_by("-created_at")

    return render(request, "client/client_home.html", {"jobs": jobs})


# ===============================
# Create Feed Post
# ===============================

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

        return redirect("client_home")

    return render(request, "projects/create_job.html")


# ===============================
# Reaction System
# ===============================

def react_job(request, id, reaction):

    job = get_object_or_404(JobPost, id=id)

    Reaction.objects.update_or_create(
        user=request.user,
        job=job,
        defaults={"reaction_type": reaction}
    )

    return redirect("client_home")


# ===============================
# Comment System
# ===============================

def comment_job(request, id):

    job = get_object_or_404(JobPost, id=id)

    if request.method == "POST":

        text = request.POST.get("comment")

        Comment.objects.create(
            user=request.user,
            job=job,
            text=text
        )

    return redirect("client_home")


# ===============================
# Post Freelancer Job
# ===============================

def post_job(request):

    if request.method == "POST":

        title = request.POST.get("title")
        description = request.POST.get("description")
        budget = request.POST.get("budget")
        skills = request.POST.get("skills")
        experience = request.POST.get("experience")

        Job.objects.create(
            client=request.user,
            title=title,
            description=description,
            budget=budget,
            skills=skills,
            experience_level=experience
        )

        return redirect("client_home")

    return render(request, "projects/post_job.html")