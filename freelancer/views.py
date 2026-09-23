from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from projects.models import Job
from .forms import FreelancerProfileForm
from .models import Project, FreelancerProfile
from django.contrib import messages
from django.http import HttpResponse
from freelancer_portal.upload_utils import validate_uploaded_image, safe_delete_unreferenced_file
User = get_user_model()
from accounts.models import Connection, ConnectionRequest
from django.shortcuts import get_object_or_404
from proposals.models import Proposal

from accounts.decorators import freelancer_required

@freelancer_required
def freelancer_home(request):
    if request.user.is_superuser:
        return redirect("accounts:admin_home")

    # Client Job Postings (Work available)
    client_jobs = Job.objects.select_related('client').filter(client__role='client').prefetch_related('comments__user', 'reactions').order_by("-created_at")
    
    applied_job_ids = set()
    if request.user.is_authenticated:
        applied_job_ids = set(Proposal.objects.filter(freelancer=request.user).values_list('job_id', flat=True))

    for job in client_jobs:
        job.has_applied = job.id in applied_job_ids
        prof = getattr(job.client, 'clientprofile', None) or getattr(job.client, 'freelancerprofile', None)
        job.author_dp = prof.profile_picture.url if (prof and getattr(prof, 'profile_picture', None)) else None
        if hasattr(job, 'skills') and job.skills:
            job.skills_list = [s.strip() for s in job.skills.split(",") if s.strip()]
        else:
            job.skills_list = []

        job.liked_by_user = job.reactions.filter(user=request.user, reaction_type='like').exists() if request.user.is_authenticated else False
        job.likes_count = job.reactions.filter(reaction_type='like').count()
        job.comments_all = job.comments.filter(parent=None).prefetch_related('reactions', 'replies__user', 'replies__reactions').distinct()
        for comment in job.comments_all:
            comment.author_dp = comment.user.get_profile_picture
            comment.likes_count = comment.reactions.filter(reaction_type='like').count()
            comment.liked_by_user = comment.reactions.filter(user=request.user, reaction_type='like').exists() if request.user.is_authenticated else False
            for reply in comment.replies.all():
                reply.author_dp = reply.user.get_profile_picture
                reply.likes_count = reply.reactions.filter(reaction_type='like').count()
                reply.liked_by_user = reply.reactions.filter(user=request.user, reaction_type='like').exists() if request.user.is_authenticated else False

        job.comments_count = job.comments.count()

    # Freelancer Posts / Talent Showcases
    from projects.models import JobPost
    freelancer_posts = JobPost.objects.select_related('client').filter(client__role='freelancer').prefetch_related('comments__user', 'reactions').order_by("-created_at")

    for post in freelancer_posts:
        prof = getattr(post.client, 'freelancerprofile', None)
        post.author_dp = prof.profile_picture.url if (prof and prof.profile_picture) else None
        if request.user.is_authenticated:
            post.liked_by_user = post.reactions.filter(user=request.user, reaction_type='like').exists()
        else:
            post.liked_by_user = False
        post.likes_count = post.reactions.filter(reaction_type='like').count()
        post.comments_all = post.comments.filter(parent=None).prefetch_related('reactions', 'replies__user', 'replies__reactions').distinct()
        for comment in post.comments_all:
            c_prof = getattr(comment.user, 'freelancerprofile', None)
            comment.author_dp = c_prof.profile_picture.url if (c_prof and c_prof.profile_picture) else None
            comment.likes_count = comment.reactions.filter(reaction_type='like').count()
            if request.user.is_authenticated:
                comment.liked_by_user = comment.reactions.filter(user=request.user, reaction_type='like').exists()
            else:
                comment.liked_by_user = False
            
            for reply in comment.replies.all():
                r_prof = getattr(reply.user, 'freelancerprofile', None)
                reply.author_dp = r_prof.profile_picture.url if (r_prof and r_prof.profile_picture) else None
                reply.likes_count = reply.reactions.filter(reaction_type='like').count()
                if request.user.is_authenticated:
                    reply.liked_by_user = reply.reactions.filter(user=request.user, reaction_type='like').exists()
                else:
                    reply.liked_by_user = False

        post.comments_count = post.comments.count()

    profile = None
    proposals_count = 0
    active_interviews_count = 0
    profile_views = 0
    
    if request.user.is_authenticated:
        profile = FreelancerProfile.objects.filter(user=request.user).first()
        proposals_count = Proposal.objects.filter(freelancer=request.user).count()
        active_interviews_count = Proposal.objects.filter(freelancer=request.user, status="accepted").count()
        if profile:
            profile_views = profile.profile_views

    context = {
        "jobs": client_jobs,
        "freelancer_posts": freelancer_posts,
        "profile": profile,
        "proposals_count": proposals_count,
        "active_interviews_count": active_interviews_count,
        "profile_views": profile_views,
    }

    return render(request, "freelancer/home.html", context)

from django.db.models import Sum
from payments.models import Payment

@freelancer_required
def freelancer_dashboard(request):
    if request.user.is_superuser:
        return redirect("accounts:admin_home")

    freelancer_profile = FreelancerProfile.objects.filter(user=request.user).first()

    recent_proposals = Proposal.objects.filter(freelancer=request.user).order_by("-created_at")[:10]
    all_proposals = Proposal.objects.filter(freelancer=request.user)

    accepted_proposals = all_proposals.filter(status="accepted")
    pending_proposals = all_proposals.filter(status="pending")

    applied_job_ids = set()
    if request.user.is_authenticated:
        applied_job_ids = set(Proposal.objects.filter(freelancer=request.user).values_list('job_id', flat=True))

    jobs = Job.objects.all().order_by("-created_at")[:6]
    for job in jobs:
        job.has_applied = job.id in applied_job_ids
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
    profile_completeness = 0
    if freelancer_profile:
        profile_completeness = freelancer_profile.profile_completeness

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

    jobs = []
    freelancers = []

    if query:
        jobs = Job.objects.filter(title__icontains=query)

        freelancers = User.objects.filter(
            role="freelancer",
            username__icontains=query
        )

    return render(request, 'search_results.html', {
        'query': query,
        'projects': jobs,
        'freelancers': freelancers
    })

from decimal import Decimal

@freelancer_required
def create_profile(request):
    if request.user.is_superuser:
        return redirect("accounts:admin_home")

    print("METHOD:", request.method)

    profile, created = FreelancerProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":
        print("POST HIT")

        profile.title = request.POST.get('title', profile.title) or ''
        profile.bio = request.POST.get('bio', profile.bio) or ''
        profile.experience_level = request.POST.get('experience_level') or profile.experience_level or 'intermediate'

        # FIX FOR DECIMAL ERROR
        hourly_rate = request.POST.get('hourly_rate')

        if hourly_rate and hourly_rate.strip():
            profile.hourly_rate = Decimal(hourly_rate)
        elif not profile.hourly_rate:
            profile.hourly_rate = Decimal("0.00")

        profile.skills = request.POST.get('skills', profile.skills) or ''
        profile.education = request.POST.get('education', profile.education) or ''
        profile.work_experience = request.POST.get('work_experience', profile.work_experience) or ''
        profile.portfolio_link = request.POST.get('portfolio_link', profile.portfolio_link) or ''
        profile.github_link = request.POST.get('github_link', profile.github_link) or ''
        profile.linkedin = request.POST.get('linkedin', profile.linkedin) or ''
        profile.country = request.POST.get('country', profile.country) or ''
        profile.city = request.POST.get('city', profile.city) or ''

        # PROFILE IMAGE
        if request.FILES.get('profile_picture'):
            pic = request.FILES['profile_picture']
            try:
                validate_uploaded_image(pic)
                old_pic = profile.profile_picture.name if profile.profile_picture else None
                profile.profile_picture = pic
                profile.save()
                if old_pic and old_pic != profile.profile_picture.name:
                    safe_delete_unreferenced_file(old_pic)
            except ValidationError as e:
                messages.error(request, e.message if hasattr(e, 'message') else str(e))
                return render(request, 'footers_file/create_profile.html', {'profile': profile})
            except Exception as e:
                messages.error(request, f"Error saving image: {str(e)}")
                return render(request, 'footers_file/create_profile.html', {'profile': profile})

        profile.save()

        print("SAVED SUCCESSFULLY")

        return redirect('/')

    return render(request, 'footers_file/create_profile.html', {
        'profile': profile
    })


from django.http import JsonResponse

@freelancer_required
def toggle_availability(request):
    if request.method == "POST":
        profile = getattr(request.user, 'freelancerprofile', None)
        if profile:
            profile.is_available = not profile.is_available
            profile.save()
            return JsonResponse({'status': 'success', 'is_available': profile.is_available})
        return JsonResponse({'status': 'error', 'message': 'Profile not found'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)


@freelancer_required
def my_proposals(request):
    proposals = Proposal.objects.filter(
        freelancer=request.user
    ).order_by("-created_at")

    return render(request, "proposals/my_proposals.html", {
        "proposals": proposals
    })



@freelancer_required
def edit_profile(request):
    user = request.user

    if request.method == "POST":
        user.username = request.POST.get("username")
        user.save()
        messages.success(request, "Account updated successfully.")
        return redirect("freelancer:edit_profile")

    from projects.models import JobPost
    showcases = JobPost.objects.filter(client=request.user).order_by('-id')

    return render(request, "freelancer/edit_profile.html", {
        "user": user,
        "showcases": showcases,
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



@freelancer_required
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

from projects.models import JobPost
from django.contrib import messages

@freelancer_required
def create_showcase(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        image = request.FILES.get("image")
        poster = request.FILES.get("poster")

        try:
            if image:
                validate_uploaded_image(image)
            if poster:
                validate_uploaded_image(poster)
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, 'message') else str(e))
            return render(request, "freelancer/create_showcase.html")

        JobPost.objects.create(
            client=request.user,
            title=title,
            description=description,
            image=image,
            poster=poster
        )
        messages.success(request, "Talent showcase posted successfully! Clients can now view your skills.")
        return redirect("/")

    return render(request, "freelancer/create_showcase.html")
@login_required
@freelancer_required
def delete_showcase(request, post_id):
    if request.method == "POST":
        post = get_object_or_404(JobPost, id=post_id, client=request.user)
        img_to_delete = post.image.name if post.image else None
        poster_to_delete = post.poster.name if hasattr(post, 'poster') and post.poster else None
        post.delete()
        if img_to_delete:
            safe_delete_unreferenced_file(img_to_delete)
        if poster_to_delete:
            safe_delete_unreferenced_file(poster_to_delete)
        messages.success(request, "Talent showcase deleted successfully.")
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'freelancer:edit_profile'
    return redirect(next_url)

from django.http import JsonResponse
from django.views.decorators.http import require_POST

@freelancer_required
@require_POST
def toggle_availability(request):
    profile = getattr(request.user, 'freelancerprofile', None)
    if profile:
        profile.is_available = not profile.is_available
        profile.save()
        return JsonResponse({'status': 'success', 'is_available': profile.is_available})
    return JsonResponse({'status': 'error', 'message': 'Profile not found'}, status=400)
