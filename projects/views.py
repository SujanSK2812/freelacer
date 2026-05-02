from django.shortcuts import render
from freelancer.models import Project
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import TruncMonth


def project_list(request):
    projects = Project.objects.all().order_by('-created_at')

    return render(request, 'projects/project_list.html', {
        'projects': projects
    })





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