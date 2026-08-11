from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from freelancer.models import Project
from projects.models import JobPost, Reaction, Comment
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import TruncMonth


def project_list(request):
    projects = Project.objects.all().order_by('-created_at')

    return render(request, 'projects/project_list.html', {
        'projects': projects
    })


@login_required
def like_job(request, job_id):
    job = get_object_or_404(JobPost, id=job_id)
    reaction, created = Reaction.objects.get_or_create(
        user=request.user,
        job=job,
        defaults={'reaction_type': 'like'}
    )
    if not created:
        reaction.delete()
    return redirect(request.META.get('HTTP_REFERER') or '/')


@login_required
def comment_job(request, job_id):
    if request.method == "POST":
        job = get_object_or_404(JobPost, id=job_id)
        text = request.POST.get("comment")
        if text:
            Comment.objects.create(
                user=request.user,
                job=job,
                text=text
            )
    return redirect(request.META.get('HTTP_REFERER') or '/')


User = get_user_model()

def reports(request):
    clients = User.objects.filter(role="client").count()
    freelancers = User.objects.filter(role="freelancer").count()

    total_users = User.objects.count()

    total_projects = Project.objects.count()
    open_projects = Project.objects.filter(status="open").count()
    completed_projects = Project.objects.filter(status="completed").count()

    # 📊 Projects per month
    projects_by_month = (
        Project.objects
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    months = [p['month'].strftime("%b %Y") for p in projects_by_month]
    counts = [p['count'] for p in projects_by_month]

    context = {
        "clients": clients,
        "freelancers": freelancers,
        "total_users": total_users,
        "total_projects": total_projects,
        "open_projects": open_projects,
        "completed_projects": completed_projects,
        "months": months,
        "counts": counts,
    }

    return render(request, "projects/reports.html", context)