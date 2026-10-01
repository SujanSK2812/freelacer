from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import timedelta
from projects.models import Job
from .forms import FreelancerProfileForm
from .models import Project, FreelancerProfile
from django.contrib import messages
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

    # Client Job Postings (Work available - open and active only)
    client_jobs = Job.objects.select_related('client').filter(
        client__role='client',
        is_active=True,
        status='open'
    ).prefetch_related('comments__user', 'reactions').order_by("-created_at")
    
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
        "active_tab": request.GET.get('tab', 'client-posts'),
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

    from projects.services import auto_complete_expired_projects
    auto_complete_expired_projects()

    freelancer_profile = FreelancerProfile.objects.filter(user=request.user).first()

    recent_proposals = Proposal.objects.filter(freelancer=request.user).order_by("-created_at")[:10]
    all_proposals = Proposal.objects.filter(freelancer=request.user)

    all_accepted_proposals = list(all_proposals.filter(status="accepted").select_related('job', 'job__client').order_by("-created_at"))
    pending_proposals = all_proposals.filter(status="pending")

    active_contracts = []
    completed_contracts = []

    for p in all_accepted_proposals:
        if not p.job.is_active or p.job.status in ['completed', 'expired']:
            p.contract_status = 'Completed'
            p.status_class = 'completed'
            completed_contracts.append(p)
        else:
            p.contract_status = 'In Progress'
            p.status_class = 'in-progress'
            active_contracts.append(p)

    applied_job_ids = set()
    if request.user.is_authenticated:
        applied_job_ids = set(Proposal.objects.filter(freelancer=request.user).values_list('job_id', flat=True))

    jobs = Job.objects.filter(is_active=True, status='open').order_by("-created_at")[:6]
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

    context = {
        "recent_proposals": recent_proposals,
        "proposals_count": all_proposals.count(),
        "pending_proposals_count": pending_proposals.count(),
        "accepted_proposals_count": len(all_accepted_proposals),
        "accepted_proposals": all_accepted_proposals,
        "active_contracts": active_contracts,
        "completed_contracts": completed_contracts,
        "active_contracts_count": len(active_contracts),
        "completed_contracts_count": len(completed_contracts),
        "total_earnings": total_earnings,
        "profile_completeness": profile_completeness,
        "freelancer": freelancer_profile,
        "skills_list": skills_list,
        "jobs": jobs,
    }

    return render(
        request,
        "freelancer/dashboard.html",
        context
    )



@login_required
def search_results(request):
    from django.db.models import Q
    from proposals.models import Proposal

    query = request.GET.get('q', '').strip()

    jobs = []
    freelancers = []

    if query:
        jobs = list(Job.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(skills__icontains=query) |
            Q(client__username__icontains=query),
            is_active=True,
            status='open'
        ).select_related('client').prefetch_related('job_proposals').order_by('-created_at'))

        applied_job_ids = set()
        if request.user.is_authenticated and getattr(request.user, 'role', '') == 'freelancer':
            applied_job_ids = set(Proposal.objects.filter(freelancer=request.user).values_list('job_id', flat=True))

        for job in jobs:
            job.has_applied = job.id in applied_job_ids
            if hasattr(job, 'skills') and job.skills:
                job.skills_list = [s.strip() for s in job.skills.split(',') if s.strip()]
            else:
                job.skills_list = []

        freelancers = list(User.objects.filter(
            role="freelancer"
        ).filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(freelancerprofile__title__icontains=query) |
            Q(freelancerprofile__skills__icontains=query)
        ).distinct().select_related('freelancerprofile'))

        for f in freelancers:
            profile = getattr(f, 'freelancerprofile', None)
            if profile and profile.skills:
                f.skills_list = [s.strip() for s in profile.skills.split(',') if s.strip()]
            else:
                f.skills_list = []

    total_count = len(jobs) + len(freelancers)

    return render(request, 'search_results.html', {
        'query': query,
        'projects': jobs,
        'freelancers': freelancers,
        'total_count': total_count
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
        if request.POST.get('remove_profile_picture') == '1':
            if profile.profile_picture:
                old_pic = profile.profile_picture.name
                profile.profile_picture = None
                profile.save()
                safe_delete_unreferenced_file(old_pic)
        elif request.FILES.get('profile_picture'):
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

        # BANNER IMAGE
        if request.POST.get('remove_banner_image') == '1' or request.POST.get('remove_banner') == '1':
            if profile.banner_image:
                old_banner = profile.banner_image.name
                profile.banner_image = None
                profile.save()
                safe_delete_unreferenced_file(old_banner)
        elif request.FILES.get('banner_image'):
            banner = request.FILES['banner_image']
            try:
                validate_uploaded_image(banner)
                old_banner = profile.banner_image.name if profile.banner_image else None
                profile.banner_image = banner
                profile.save()
                if old_banner and old_banner != profile.banner_image.name:
                    safe_delete_unreferenced_file(old_banner)
            except ValidationError as e:
                messages.error(request, e.message if hasattr(e, 'message') else str(e))
                return render(request, 'footers_file/create_profile.html', {'profile': profile})
            except Exception as e:
                messages.error(request, f"Error saving banner image: {str(e)}")
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
    profile, _ = FreelancerProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        new_username = request.POST.get("username", "").strip()
        new_email = request.POST.get("email", "").strip()
        new_phone = request.POST.get("phone", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        title = request.POST.get("title", "").strip()
        hourly_rate = request.POST.get("hourly_rate", "").strip()
        city = request.POST.get("city", "").strip()
        country = request.POST.get("country", "").strip()
        bio = request.POST.get("bio", "").strip()

        has_error = False

        if new_username:
            if User.objects.filter(username__iexact=new_username).exclude(id=user.id).exists():
                messages.error(request, "This username is already taken by another account.")
                has_error = True
            else:
                user.username = new_username

        if new_email:
            if User.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
                messages.error(request, "This email is already registered to another account.")
                has_error = True
            else:
                user.email = new_email

        if new_phone:
            if User.objects.filter(phone=new_phone).exclude(id=user.id).exists():
                messages.error(request, "This phone number is already registered to another account.")
                has_error = True
            else:
                user.phone = new_phone

        if not has_error:
            user.first_name = first_name
            user.last_name = last_name
            user.save()

            profile.title = title
            profile.city = city
            profile.country = country
            profile.bio = bio

            if hourly_rate:
                try:
                    profile.hourly_rate = Decimal(hourly_rate)
                except Exception:
                    pass
            elif hourly_rate == "":
                profile.hourly_rate = None

            # Profile Picture Removal
            if request.POST.get('remove_profile_picture') == '1':
                if profile.profile_picture:
                    old_pic = profile.profile_picture.name
                    profile.profile_picture = None
                    profile.save()
                    safe_delete_unreferenced_file(old_pic)
            # Profile Picture Upload
            elif request.FILES.get('profile_picture'):
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
                    has_error = True
                except Exception as e:
                    messages.error(request, f"Error saving profile picture: {str(e)}")
            # Banner Image Removal
            if request.POST.get('remove_banner_image') == '1' or request.POST.get('remove_banner') == '1':
                if profile.banner_image:
                    old_banner = profile.banner_image.name
                    profile.banner_image = None
                    profile.save()
                    safe_delete_unreferenced_file(old_banner)
            # Banner Image Upload
            elif request.FILES.get('banner_image'):
                banner = request.FILES['banner_image']
                try:
                    validate_uploaded_image(banner)
                    old_banner = profile.banner_image.name if profile.banner_image else None
                    profile.banner_image = banner
                    profile.save()
                    if old_banner and old_banner != profile.banner_image.name:
                        safe_delete_unreferenced_file(old_banner)
                except ValidationError as e:
                    messages.error(request, e.message if hasattr(e, 'message') else str(e))
                    has_error = True
                except Exception as e:
                    messages.error(request, f"Error saving banner image: {str(e)}")
                    has_error = True

            if not has_error:
                profile.save()
                messages.success(request, "Account details updated successfully.")
                return redirect("freelancer:edit_profile")

    from projects.models import JobPost
    showcases = JobPost.objects.filter(client=request.user).order_by('-id')

    return render(request, "freelancer/edit_profile.html", {
        "user": user,
        "profile": profile,
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

    # Mutual / Accepted Connections
    freelancer_sent_ids = set(Connection.objects.filter(sender=freelancer).values_list('receiver_id', flat=True))
    freelancer_received_ids = set(Connection.objects.filter(receiver=freelancer).values_list('sender_id', flat=True))
    connections_count = len((freelancer_sent_ids | freelancer_received_ids) - {freelancer.id})

    # Followers & Following counts
    followers_count = Connection.objects.filter(receiver=freelancer).count()
    following_count = Connection.objects.filter(sender=freelancer).count()

    # Other professionals / People you may know for the aside
    other_freelancers = User.objects.filter(role="freelancer").exclude(id=freelancer.id).select_related('freelancerprofile')[:5]

    context = {
        "freelancer": freelancer,
        "profile": profile,
        "requested_ids": requested_ids,
        "connected_ids": connected_ids,
        "connections_count": connections_count,
        "followers_count": followers_count,
        "following_count": following_count,
        "other_freelancers": other_freelancers,
    }

    return render(
        request,
        "freelancer/freelancer_profile.html",
        context
    )



@freelancer_required
def freelancer_connections(request):
    sent_ids = set(Connection.objects.filter(sender=request.user).values_list('receiver_id', flat=True))
    received_ids = set(Connection.objects.filter(receiver=request.user).values_list('sender_id', flat=True))
    connected_ids = (sent_ids | received_ids) - {request.user.id}

    connected_users = list(User.objects.filter(id__in=connected_ids))

    return render(
        request,
        'freelancer/connections.html',
        {
            'connected_users': connected_users,
            'connections_count': len(connected_users),
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
        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()
        image = request.FILES.get("image")
        poster = request.FILES.get("poster")

        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json'

        if not title or not description:
            err_msg = "Please provide both a title and description for your showcase."
            if is_ajax:
                return JsonResponse({"status": "error", "message": err_msg}, status=400)
            messages.error(request, err_msg)
            return render(request, "freelancer/create_showcase.html")

        try:
            if image:
                validate_uploaded_image(image)
            if poster:
                validate_uploaded_image(poster)
        except ValidationError as e:
            err_msg = e.message if hasattr(e, 'message') else str(e)
            if is_ajax:
                return JsonResponse({"status": "error", "message": err_msg}, status=400)
            messages.error(request, err_msg)
            return render(request, "freelancer/create_showcase.html")

        # Deduplication check: prevent duplicate posts if user clicks Submit multiple times
        recent_duplicate = JobPost.objects.filter(
            client=request.user,
            title=title,
            created_at__gte=timezone.now() - timedelta(seconds=5)
        ).first()

        if not recent_duplicate:
            JobPost.objects.create(
                client=request.user,
                title=title,
                description=description,
                image=image,
                poster=poster
            )

        redirect_url = reverse("freelancer:freelancer_home") + "?tab=freelancer-posts"

        if is_ajax:
            return JsonResponse({
                "status": "success",
                "message": "Post uploaded successfully!",
                "redirect_url": redirect_url
            })

        messages.success(request, "Post uploaded successfully!")
        return redirect(redirect_url)

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


@freelancer_required
def active_contracts(request):
    if request.user.is_superuser:
        return redirect("accounts:admin_home")

    from projects.services import auto_complete_expired_projects
    auto_complete_expired_projects()

    accepted_proposals = list(Proposal.objects.filter(
        freelancer=request.user,
        status='accepted'
    ).select_related('job', 'job__client').order_by('-created_at'))

    total_contract_value = sum(p.bid_amount for p in accepted_proposals)

    active_contracts = []
    completed_contracts = []

    for proposal in accepted_proposals:
        prof = getattr(proposal.job.client, 'clientprofile', None) or getattr(proposal.job.client, 'freelancerprofile', None)
        proposal.client_avatar = prof.profile_picture.url if (prof and getattr(prof, 'profile_picture', None)) else None
        proposal.client_company = getattr(prof, 'company_name', None) or 'Direct Client'
        if hasattr(proposal.job, 'skills') and proposal.job.skills:
            proposal.skills_list = [s.strip() for s in proposal.job.skills.split(",") if s.strip()]
        else:
            proposal.skills_list = []

        if not proposal.job.is_active or proposal.job.status in ['completed', 'expired']:
            proposal.is_completed = True
            proposal.contract_status = 'Completed'
            proposal.status_badge_class = 'badge-completed-contract'
            completed_contracts.append(proposal)
        else:
            proposal.is_completed = False
            proposal.contract_status = 'In Progress'
            proposal.status_badge_class = 'badge-active-contract'
            active_contracts.append(proposal)

    pending_count = Proposal.objects.filter(freelancer=request.user, status='pending').count()

    return render(request, "freelancer/active_contracts.html", {
        "accepted_proposals": accepted_proposals,
        "active_contracts": active_contracts,
        "completed_contracts": completed_contracts,
        "active_contracts_count": len(active_contracts),
        "completed_contracts_count": len(completed_contracts),
        "total_contract_value": total_contract_value,
        "pending_count": pending_count,
    })


@login_required
@freelancer_required
def update_freelancer_banner(request):
    profile, _ = FreelancerProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        if request.POST.get('action') == 'delete' or request.POST.get('remove_banner_image') == '1':
            if profile.banner_image:
                old_banner = profile.banner_image.name
                profile.banner_image = None
                profile.save()
                safe_delete_unreferenced_file(old_banner)
                messages.success(request, "Banner removed successfully.")
        elif request.FILES.get('banner_image'):
            banner = request.FILES['banner_image']
            try:
                validate_uploaded_image(banner)
                old_banner = profile.banner_image.name if profile.banner_image else None
                profile.banner_image = banner
                profile.save()
                if old_banner and old_banner != profile.banner_image.name:
                    safe_delete_unreferenced_file(old_banner)
                messages.success(request, "Banner image updated successfully.")
            except ValidationError as e:
                messages.error(request, e.message if hasattr(e, 'message') else str(e))
            except Exception as e:
                messages.error(request, f"Error saving banner image: {str(e)}")

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('freelancer:freelancer_profile', freelancer_id=request.user.id)

