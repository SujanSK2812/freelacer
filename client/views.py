from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from accounts.decorators import client_required
from projects.models import JobPost, Job
from django.contrib.auth import get_user_model
from freelancer_portal.upload_utils import validate_uploaded_image, safe_delete_unreferenced_file

User = get_user_model()


@client_required
def client_home(request):
    if request.user.is_superuser:
        return redirect("accounts:admin_home")

    # Client Job Postings (Work available - open and active only)
    client_jobs = Job.objects.select_related('client').filter(
        client__role='client',
        is_active=True,
        status='open'
    ).prefetch_related('comments__user', 'reactions').order_by("-created_at")
    for job in client_jobs:
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
    freelancer_posts = JobPost.objects.select_related('client').filter(client__role='freelancer').prefetch_related('comments__user', 'reactions').order_by("-created_at")

    for post in freelancer_posts:
        post.author_dp = post.client.get_profile_picture
        post.liked_by_user = post.reactions.filter(user=request.user, reaction_type='like').exists() if request.user.is_authenticated else False
        post.likes_count = post.reactions.filter(reaction_type='like').count()
        post.comments_all = post.comments.filter(parent=None).prefetch_related('reactions', 'replies__user', 'replies__reactions').distinct()
        for comment in post.comments_all:
            comment.author_dp = comment.user.get_profile_picture
            comment.likes_count = comment.reactions.filter(reaction_type='like').count()
            comment.liked_by_user = comment.reactions.filter(user=request.user, reaction_type='like').exists() if request.user.is_authenticated else False
            for reply in comment.replies.all():
                reply.author_dp = reply.user.get_profile_picture
                reply.likes_count = reply.reactions.filter(reaction_type='like').count()
                reply.liked_by_user = reply.reactions.filter(user=request.user, reaction_type='like').exists() if request.user.is_authenticated else False

        post.comments_count = post.comments.count()

    freelancers = User.objects.filter(role="freelancer")

    from collections import Counter
    from freelancer.models import FreelancerProfile
    from proposals.models import Proposal
    
    skill_counts = Counter()
    for prof in FreelancerProfile.objects.exclude(skills__isnull=True).exclude(skills__exact=""):
        for skill in prof.get_skills_list():
            skill_counts[skill] += 1
            
    top_categories = [{"title": skill, "count": count} for skill, count in skill_counts.most_common(5)]

    total_freelancers_count = User.objects.filter(role="freelancer").count()
    total_jobs_count = client_jobs.count()
    total_proposals_count = Proposal.objects.filter(job__client=request.user).count()

    return render(request, "client/home.html", {
        "freelancers": freelancers,
        "jobs": client_jobs,
        "freelancer_posts": freelancer_posts,
        "top_categories": top_categories,
        "total_freelancers_count": total_freelancers_count,
        "total_jobs_count": total_jobs_count,
        "total_proposals_count": total_proposals_count,
    })


from proposals.models import Proposal

@client_required
def client_dashboard(request):
    from projects.services import auto_complete_expired_projects
    auto_complete_expired_projects()

    client_profile = getattr(request.user, 'clientprofile', None)
    all_client_jobs = list(Job.objects.filter(client=request.user).prefetch_related('job_proposals__freelancer').order_by('-created_at'))
    
    proposals_count = Proposal.objects.filter(job__client=request.user).count()
    
    # Hire count is the number of proposals accepted by this client
    hired_count = Proposal.objects.filter(job__client=request.user, status='accepted').count()

    from accounts.models import Testimonial
    from django.db.models import Avg
    avg_rating = Testimonial.objects.filter(user=request.user).aggregate(Avg('rating'))['rating__avg']
    client_rating = f"{avg_rating:.1f}" if avg_rating else "0.0"
    
    recommended_freelancers = User.objects.filter(role="freelancer")[:5]
    
    active_jobs = []
    completed_jobs = []

    for job in all_client_jobs:
        job.proposal_count = job.job_proposals.count()
        accepted_prop = job.accepted_proposal
        job.accepted_bid = accepted_prop
        
        if job.status == 'completed':
            job.status_label = 'Completed'
            job.status_class = 'status-completed'
            completed_jobs.append(job)
        elif job.status == 'expired':
            job.status_label = 'Expired'
            job.status_class = 'status-expired'
            completed_jobs.append(job)
        elif not job.is_active:
            job.status_label = 'Inactive'
            job.status_class = 'status-expired'
            completed_jobs.append(job)
        elif job.status == 'in_progress':
            job.status_label = 'In Progress'
            job.status_class = 'status-in-progress'
            active_jobs.append(job)
        else:
            job.status_label = 'Open'
            job.status_class = 'status-open'
            active_jobs.append(job)

    active_jobs_count = len(active_jobs)
    completed_jobs_count = len(completed_jobs)

    recent_activities = Proposal.objects.filter(job__client=request.user).order_by('-created_at')[:5]

    import random
    banner_images = [
        "images/banners/freelance_banner_1.jpg",
        "images/banners/freelance_banner_2.jpg",
        "images/banners/freelance_banner_3.jpg",
        "images/banners/freelance_banner_4.jpg",
    ]
    random_banner = random.choice(banner_images)

    return render(request, "client/dashboard.html", {
        "client_profile": client_profile,
        "client_jobs": all_client_jobs,
        "active_jobs": active_jobs,
        "completed_jobs": completed_jobs,
        "active_jobs_count": active_jobs_count,
        "completed_jobs_count": completed_jobs_count,
        "proposals_count": proposals_count,
        "hired_count": hired_count,
        "client_rating": client_rating,
        "recommended_freelancers": recommended_freelancers,
        "recent_activities": recent_activities,
        "random_banner": random_banner,
    })

@client_required
def create_job(request):
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()
        budget = request.POST.get("budget", "5000")
        skills = request.POST.get("skills", "Python, Web Development")
        experience_level = request.POST.get("experience_level", "Intermediate")
        image = request.FILES.get("image")
        poster = request.FILES.get("poster")

        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json'

        if not title or not description:
            err_msg = "Please provide both a job title and description."
            if is_ajax:
                return JsonResponse({"status": "error", "message": err_msg}, status=400)
            messages.error(request, err_msg)
            return render(request, "client/create_job.html", {"is_client": True})

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
            return render(request, "client/create_job.html", {"is_client": True})

        # Deduplication check: prevent duplicate posts if user clicks Submit multiple times
        recent_duplicate = Job.objects.filter(
            client=request.user,
            title=title,
            created_at__gte=timezone.now() - timedelta(seconds=5)
        ).first()

        if not recent_duplicate:
            Job.objects.create(
                client=request.user,
                title=title,
                description=description,
                budget=budget,
                skills=skills,
                experience_level=experience_level,
                image=image,
                poster=poster
            )

        redirect_url = reverse("client:client_home")

        if is_ajax:
            return JsonResponse({
                "status": "success",
                "message": "Post uploaded successfully!",
                "redirect_url": redirect_url
            })

        messages.success(request, "Post uploaded successfully!")
        return redirect(redirect_url)

    return render(request, "client/create_job.html", {"is_client": True})


@client_required
def all_freelancers(request):
    from accounts.models import Connection, ConnectionRequest
    freelancers = User.objects.filter(role="freelancer").select_related('freelancerprofile')

    requested_ids = list(ConnectionRequest.objects.filter(
        sender=request.user
    ).values_list("receiver_id", flat=True))

    connected_ids = list(Connection.objects.filter(
        sender=request.user
    ).values_list("receiver_id", flat=True))

    return render(request, "client/all_freelancers.html", {
        "freelancers": freelancers,
        "requested_ids": requested_ids,
        "connected_ids": connected_ids,
    })


@login_required
def job_detail(request, job_id):
    from proposals.models import Proposal
    job = Job.objects.filter(id=job_id).first()
    if not job:
        job = get_object_or_404(JobPost, id=job_id)

    # Attach convenience attributes if it's a Job model instance
    if hasattr(job, 'experience_level') and not hasattr(job, 'experience_required'):
        setattr(job, 'experience_required', job.experience_level)
    if hasattr(job, 'skills') and not hasattr(job, 'category'):
        setattr(job, 'category', job.skills)

    # Parse skills
    skills_list = []
    if hasattr(job, 'skills') and job.skills:
        skills_list = [s.strip() for s in job.skills.split(',') if s.strip()]

    # Proposals count
    proposals_count = 0
    if hasattr(job, 'job_proposals'):
        proposals_count = job.job_proposals.count()

    # Check if current user has applied
    has_applied = False
    if request.user.is_authenticated and getattr(request.user, 'role', '') == 'freelancer':
        has_applied = Proposal.objects.filter(job=job, freelancer=request.user).exists()

    # Client information & stats
    client_profile = getattr(job.client, 'clientprofile', None)
    client_jobs_count = Job.objects.filter(client=job.client).count()
    client_hires_count = Proposal.objects.filter(job__client=job.client, status='accepted').count()
    is_owner = bool(request.user.is_authenticated and request.user.id == job.client.id)

    return render(request, "client/job_detail.html", {
        "job": job,
        "skills_list": skills_list,
        "proposals_count": proposals_count,
        "has_applied": has_applied,
        "client_profile": client_profile,
        "client_jobs_count": client_jobs_count,
        "client_hires_count": client_hires_count,
        "is_owner": is_owner,
    })
@client_required
def client_profile(request):
    return redirect('accounts:view_profile', user_id=request.user.id)

@client_required
def edit_client_profile(request):
    from client.models import ClientProfile
    
    profile, created = ClientProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        # Update User
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.save()
        
        # Update Profile
        profile.company_name = request.POST.get('company_name', profile.company_name)
        profile.bio = request.POST.get('bio', profile.bio)
        profile.website = request.POST.get('website', profile.website)
        profile.country = request.POST.get('country', profile.country)
        profile.city = request.POST.get('city', profile.city)
        
        # Profile Picture Upload
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
                return render(request, "client/edit_profile.html", {"profile": profile})
            except Exception as e:
                messages.error(request, f"Error saving image: {str(e)}")
                return render(request, "client/edit_profile.html", {"profile": profile})

        # Banner Image Upload
        if request.POST.get('remove_banner') == '1':
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
                return render(request, "client/edit_profile.html", {"profile": profile})
            except Exception as e:
                messages.error(request, f"Error saving banner image: {str(e)}")
                return render(request, "client/edit_profile.html", {"profile": profile})

        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("client:client_profile")

    from projects.models import Job
    jobs = Job.objects.filter(client=request.user).order_by('-id')

    return render(request, "client/edit_profile.html", {
        "profile": profile,
        "jobs": jobs
    })


@login_required
@client_required
def update_client_banner(request):
    from client.models import ClientProfile
    profile, _ = ClientProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        if request.POST.get('action') == 'delete':
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
        else:
            messages.warning(request, "Please select an image file for your banner.")

    return redirect('accounts:view_profile', user_id=request.user.id)
@login_required
@client_required
def delete_job(request, job_id):
    if request.method == "POST":
        job = get_object_or_404(Job, id=job_id, client=request.user)
        img_to_delete = job.image.name if job.image else None
        poster_to_delete = job.poster.name if hasattr(job, 'poster') and job.poster else None
        job.delete()
        if img_to_delete:
            safe_delete_unreferenced_file(img_to_delete)
        if poster_to_delete:
            safe_delete_unreferenced_file(poster_to_delete)
        messages.success(request, "Job deleted successfully.")
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'client:client_profile'
    return redirect(next_url)
@login_required
def client_proposals(request):
    if getattr(request.user, 'role', '') == 'freelancer':
        return redirect('freelancer:my_proposals')

    if getattr(request.user, 'role', '') != 'client' and not request.user.is_superuser:
        return redirect('home')

    from proposals.models import Proposal
    from django.db.models import Q
    
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')

    proposals = Proposal.objects.filter(job__client=request.user).select_related('freelancer', 'job')

    if status_filter and status_filter in ['pending', 'accepted', 'rejected']:
        proposals = proposals.filter(status=status_filter)
        
    if search_query:
        proposals = proposals.filter(
            Q(freelancer__username__icontains=search_query) |
            Q(job__title__icontains=search_query)
        )

    proposals = proposals.order_by('-created_at')

    # Find which jobs already have an accepted proposal
    accepted_job_ids = set(
        Proposal.objects.filter(job__client=request.user, status='accepted').values_list('job_id', flat=True)
    )

    from payments.models import Payment
    paid_payments_map = {
        pm.proposal_id: pm
        for pm in Payment.objects.filter(client=request.user, paid=True)
    }

    for p in proposals:
        p.job_already_accepted = p.job_id in accepted_job_ids
        p.freelancer_dp = p.freelancer.get_profile_picture
        p.payment = paid_payments_map.get(p.id)
        p.is_paid = p.payment is not None
    
    return render(request, "client/proposals.html", {
        "proposals": proposals,
        "current_status": status_filter,
        "search_query": search_query
    })

@login_required
@client_required
def accept_proposal(request, proposal_id):
    from proposals.models import Proposal
    from accounts.models import Notification
    from django.urls import reverse
    if request.method == "POST":
        proposal = get_object_or_404(Proposal, id=proposal_id, job__client=request.user)

        # Check if a proposal has already been accepted for this job
        if Proposal.objects.filter(job=proposal.job, status='accepted').exists():
            messages.error(
                request,
                f"A bid has already been accepted for '{proposal.job.title}'. You cannot accept another freelancer's bid."
            )
            return redirect('client:client_proposals')

        if proposal.status == 'pending':
            now = timezone.now()
            proposal.status = 'accepted'
            proposal.accepted_at = now
            proposal.save()

            # Update Job status and calculate expected completion date from accepted bid's delivery days
            job = proposal.job
            job.status = 'in_progress'
            job.is_active = True
            job.accepted_at = now
            job.expected_completion_date = now + timedelta(days=proposal.delivery_days)
            job.save(update_fields=['status', 'is_active', 'accepted_at', 'expected_completion_date'])

            # Notify the accepted freelancer
            Notification.objects.create(
                user=proposal.freelancer,
                notification_type='proposal_status',
                message=f"🎉 Your proposal for <strong>{proposal.job.title}</strong> has been <strong>accepted</strong> by {request.user.username}!",
                link=reverse('freelancer:my_proposals')
            )

            # Auto-reject remaining pending proposals for this job and notify them
            other_pending = Proposal.objects.filter(job=proposal.job, status='pending').exclude(id=proposal.id)
            for other in other_pending:
                other.status = 'rejected'
                other.save()
                Notification.objects.create(
                    user=other.freelancer,
                    notification_type='proposal_status',
                    message=f"The job <strong>{proposal.job.title}</strong> has been awarded to another freelancer. Your proposal was not selected.",
                    link=reverse('freelancer:my_proposals')
                )

            messages.success(
                request,
                f"Proposal from {proposal.freelancer.username} accepted! Please proceed to make payment of ₹{proposal.bid_amount} to fund the project contract."
            )
            return redirect('payments:checkout', proposal_id=proposal.id)
        else:
            messages.info(request, f"This proposal has already been processed ({proposal.status}).")
    return redirect('client:client_proposals')

@login_required
@client_required
def reject_proposal(request, proposal_id):
    from proposals.models import Proposal
    from accounts.models import Notification
    from django.urls import reverse
    if request.method == "POST":
        proposal = get_object_or_404(Proposal, id=proposal_id, job__client=request.user)
        if proposal.status == 'pending':
            proposal.status = 'rejected'
            proposal.save()
            # Notify the freelancer
            Notification.objects.create(
                user=proposal.freelancer,
                notification_type='proposal_status',
                message=f"Your proposal for <strong>{proposal.job.title}</strong> was not selected this time. Keep applying!",
                link=reverse('freelancer:my_proposals')
            )
            messages.success(request, f"Proposal from {proposal.freelancer.username} rejected.")
    return redirect('client:client_proposals')
