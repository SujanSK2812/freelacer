from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from accounts.decorators import client_required
from projects.models import JobPost, Job
from django.contrib.auth import get_user_model
from freelancer_portal.upload_utils import validate_uploaded_image, safe_delete_unreferenced_file

User = get_user_model()


@client_required
def client_home(request):
    if request.user.is_superuser:
        return redirect("accounts:admin_home")

    # Client Job Postings (Work available)
    client_jobs = Job.objects.select_related('client').filter(client__role='client').prefetch_related('comments__user', 'reactions').order_by("-created_at")
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

    from django.db.models import Count
    from freelancer.models import FreelancerProfile
    
    top_categories = (
        FreelancerProfile.objects.exclude(title__isnull=True)
        .exclude(title__exact="")
        .values("title")
        .annotate(count=Count("title"))
        .order_by("-count")[:5]
    )

    return render(request, "client/home.html", {
        "freelancers": freelancers,
        "jobs": client_jobs,
        "freelancer_posts": freelancer_posts,
        "top_categories": top_categories,
    })


from proposals.models import Proposal

@client_required
def client_dashboard(request):
    client_profile = getattr(request.user, 'clientprofile', None)
    client_jobs = Job.objects.filter(client=request.user).order_by('-created_at')
    
    active_jobs_count = client_jobs.count()
    proposals_count = Proposal.objects.filter(job__client=request.user).count()
    
    recommended_freelancers = User.objects.filter(role="freelancer")[:5]
    
    for job in client_jobs:
        job.proposal_count = Proposal.objects.filter(job=job).count()
        if Proposal.objects.filter(job=job, status='accepted').exists():
            job.status = 'In Progress'
            job.status_class = 'status-in-progress'
        else:
            job.status = 'Open'
            job.status_class = 'status-open'

    recent_activities = Proposal.objects.filter(job__client=request.user).order_by('-created_at')[:5]

    return render(request, "client/dashboard.html", {
        "client_profile": client_profile,
        "client_jobs": client_jobs,
        "active_jobs_count": active_jobs_count,
        "proposals_count": proposals_count,
        "recommended_freelancers": recommended_freelancers,
        "recent_activities": recent_activities,
    })

@client_required
def create_job(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        budget = request.POST.get("budget", "5000")
        skills = request.POST.get("skills", "Python, Web Development")
        experience_level = request.POST.get("experience_level", "Intermediate")
        image = request.FILES.get("image")
        poster = request.FILES.get("poster")

        try:
            if image:
                validate_uploaded_image(image)
            if poster:
                validate_uploaded_image(poster)
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, 'message') else str(e))
            return render(request, "client/create_job.html", {"is_client": True})

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
        messages.success(request, "Work posted successfully! Freelancers can now view it and submit proposals.")
        return redirect("/")

    return render(request, "client/create_job.html", {"is_client": True})


@client_required
def all_freelancers(request):

    freelancers = User.objects.filter(role="freelancer")

    return render(request, "client/all_freelancers.html", {
        "freelancers": freelancers
    })


@login_required
def job_detail(request, job_id):
    job = Job.objects.filter(id=job_id).first()
    if not job:
        job = get_object_or_404(JobPost, id=job_id)

    # Attach convenience attributes if it's a Job model instance
    if hasattr(job, 'experience_level') and not hasattr(job, 'experience_required'):
        setattr(job, 'experience_required', job.experience_level)
    if hasattr(job, 'skills') and not hasattr(job, 'category'):
        setattr(job, 'category', job.skills)

    return render(request, "client/job_detail.html", {
        "job": job
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
@client_required
def client_proposals(request):
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
            proposal.status = 'accepted'
            proposal.save()

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
