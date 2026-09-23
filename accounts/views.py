
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.decorators import login_required
from freelancer.models import Project
from .models import EmailOTP, Testimonial
from .utils import send_portal_email
from freelancer.models import FreelancerProfile

User = get_user_model()


def get_user_dashboard_redirect(user):
    """
    Redirect an authenticated user based strictly on their role stored in the database:
    - Admin (is_superuser, is_staff, or role=='admin') -> accounts:admin_home
    - Client -> client:client_dashboard
    - Freelancer -> freelancer:freelancer_dashboard
    """
    if not getattr(user, "is_authenticated", False):
        return redirect("accounts:login")

    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False) or (getattr(user, "role", None) or "").lower() == "admin":
        return redirect("accounts:admin_home")

    role = (getattr(user, "role", None) or "").lower()
    if role == "client":
        return redirect("client:client_dashboard")
    elif role == "freelancer":
        return redirect("freelancer:freelancer_dashboard")

    return redirect("home")


def register(request, role=None):
    if request.user.is_authenticated:
        return get_user_dashboard_redirect(request.user)
    return select_role(request, role=role)


def verify_otp(request, user_id):
    if request.user.is_authenticated:
        return get_user_dashboard_redirect(request.user)

    user = get_object_or_404(User, id=user_id)

    if user.is_active:
        messages.info(request, "Account is already verified. Please log in.")
        return redirect("accounts:login")

    otp_obj = EmailOTP.objects.filter(user=user).last()

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        auto_verify = request.POST.get("auto_verify") == "true"

        if (auto_verify and settings.DEBUG) or (otp_obj and otp_obj.otp == entered_otp and otp_obj.is_valid()):
            user.is_active = True
            user.save()
            if otp_obj:
                otp_obj.delete()
            messages.success(request, "Account verified successfully! Please log in.")
            return redirect("accounts:login")
        else:
            messages.error(request, "Invalid or expired OTP. Please try again.")

    context = {
        "user_obj": user,
        "email": user.email,
        "debug_otp": otp_obj.otp if (settings.DEBUG and otp_obj) else None
    }
    return render(request, "accounts/verify_otp.html", context)


def resend_otp(request, user_id):
    if request.user.is_authenticated:
        return get_user_dashboard_redirect(request.user)

    user = get_object_or_404(User, id=user_id)

    if user.is_active:
        messages.info(request, "Account is already verified. Please log in.")
        return redirect("accounts:login")

    EmailOTP.objects.filter(user=user).delete()
    otp_code = EmailOTP.generate_otp()
    EmailOTP.objects.create(user=user, otp=otp_code)

    send_portal_email(
        "Your Verification OTP - Freelancer Portal",
        f"Hi {user.username},\n\nYour new verification OTP code is: {otp_code}\n\nThis OTP is valid for 5 minutes.",
        [user.email],
    )

    messages.success(request, f"A new OTP has been sent to {user.email}.")
    return redirect("accounts:verify_otp", user_id=user.id)



# def user_login(request):

#     if request.method == "POST":
#         email = request.POST.get("email")
#         password = request.POST.get("password")

#         user = authenticate(request, email=email, password=password)

#         if user is not None:
#             login(request, user)

#             # Check role from Profile
#             if user.profile.role == "client":
#                 return redirect("/client/dashboard/")
#             else:
#                 return redirect("/freelancer/dashboard/")

#         else:
#             messages.error(request, "Invalid email or password")

#     return render(request, "accounts/login.html")

# def select_role(request):

#     role = request.GET.get("role")

#     # If no role selected → show role selection page
#     if not role:
#         return render(request, "accounts/select_role.html")

#     # If form submitted
#     if request.method == "POST":

#         username = request.POST.get("username")
#         email = request.POST.get("email")
#         phone = request.POST.get("phone")
#         password = request.POST.get("password")
#         role = request.POST.get("role")

#         # Check phone uniqueness
#         if User.objects.filter(phone=phone).exists():
#             messages.error(request, "Phone number already registered.")
#             return redirect(request.path + f"?role={role}")

#         # Check email uniqueness
#         if User.objects.filter(email=email).exists():
#             messages.error(request, "Email already registered.")
#             return redirect(request.path + f"?role={role}")

#         # Check username uniqueness
#         if User.objects.filter(username=username).exists():
#             messages.error(request, "Username already taken.")
#             return redirect(request.path + f"?role={role}")

#         # Create user
#         user = User.objects.create_user(
#             username=username,
#             email=email,
#             password=password,
#             phone=phone,
#             role=role
#         )

#         messages.success(request, "Account created successfully!")
#         return redirect("login")

#     # If GET request → show register page
#     return render(request, "accounts/register.html", {"role": role})
def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            current_site = get_current_site(request)
            reset_link = f"http://{current_site.domain}{reverse('accounts:password_reset_confirm', args=[uid, token])}"

            subject = "Reset Your Password - Freelancer Portal"
            body = f"Hi {user.username},\n\nYou requested a password reset for your Freelancer Portal account.\n\nClick the link below to set a new password:\n{reset_link}\n\nIf you did not request this, please ignore this email."

            send_portal_email(subject, body, [email])

            if settings.DEBUG:
                messages.success(request, f"Password reset link generated! Link: {reset_link}")
            else:
                messages.success(request, "Password reset link sent to your email. Please check your inbox.")
        else:
            messages.error(request, "No account found with that email address.")

    return render(request, "accounts/password_reset.html")


def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if not user or not default_token_generator.check_token(user, token):
        messages.error(request, "Password reset link is invalid or has expired.")
        return redirect("accounts:password-reset")

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "accounts/password_reset_confirm.html", {"uidb64": uidb64, "token": token})

        user.set_password(password)
        user.save()
        messages.success(request, "Your password has been reset successfully. Please log in.")
        return redirect("accounts:login")

    return render(request, "accounts/password_reset_confirm.html", {"uidb64": uidb64, "token": token})





# ==========================
# REGISTER (ROLE BASED)
# ==========================
def select_role(request, role=None):
    # Strict security check: authenticated users must NEVER access registration or role selection
    if request.user.is_authenticated:
        return get_user_dashboard_redirect(request.user)

    role = (role or request.GET.get("role") or "").lower()

    # If role not selected or invalid → show role selection page
    if not role or role not in ["client", "freelancer"]:
        return render(request, "accounts/select_role.html")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password")
        post_role = (request.POST.get("role") or role).lower()
        if post_role not in ["client", "freelancer"]:
            post_role = "client"

        # Uniqueness checks
        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email already registered.")
            return redirect(f"{request.path}?role={post_role}")

        if User.objects.filter(phone=phone).exists():
            messages.error(request, "Phone already registered.")
            return redirect(f"{request.path}?role={post_role}")

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Username already taken.")
            return redirect(f"{request.path}?role={post_role}")

        # Create user (inactive until activation)
        user = User.objects.create_user(
            username=username,
            email=email,
            phone=phone,
            password=password,
            role=post_role,
            is_active=False
        )

        # Generate 6-digit OTP
        EmailOTP.objects.filter(user=user).delete()
        otp_code = EmailOTP.generate_otp()
        EmailOTP.objects.create(user=user, otp=otp_code)

        send_portal_email(
            "Your Verification OTP - Freelancer Portal",
            f"Hi {username},\n\nYour OTP for activating your Freelancer Portal account is: {otp_code}\n\nThis OTP is valid for 5 minutes.",
            [email],
        )

        messages.success(request, f"Account created! Please enter the 6-digit OTP sent to {email}.")
        return redirect("accounts:verify_otp", user_id=user.id)

    return render(request, "accounts/register.html", {"role": role})


# ==========================
# ACTIVATE ACCOUNT
# ==========================
def activate_account(request, uidb64, token):

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Account activated successfully. Please login.")
    else:
        messages.error(request, "Activation link is invalid.")

    return redirect("accounts:login")


# ==========================
# LOGIN
# ==========================

def user_login(request):
    if request.user.is_authenticated:
        return get_user_dashboard_redirect(request.user)

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password")

        user = None

        # Try login using EMAIL (normal users)
        try:
            user_obj = User.objects.get(email__iexact=email)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            pass

        # Try login using USERNAME (for admin)
        if user is None:
            user = authenticate(request, username=email, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "Activate your account first.")
                return redirect("accounts:login")

            login(request, user)
            return get_user_dashboard_redirect(user)
        else:
            messages.error(request, "Invalid email or password")

    return render(request, "accounts/login.html")


# ==========================
# LOGOUT
# ==========================
def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def role_redirect(request, role):
    # Role comes strictly from the authenticated user's database record!
    return get_user_dashboard_redirect(request.user)




@login_required
def admin_home(request):

    if not request.user.is_superuser:
        return redirect("accounts:login")

    clients = User.objects.filter(role="client")
    freelancers = User.objects.filter(role="freelancer")
    projects = Project.objects.all()

    context = {
        "client_count": clients.count(),
        "freelancer_count": freelancers.count(),
        "project_count": projects.count(),
        "total_count": clients.count() + freelancers.count(),
    }

    return render(request, "admin/home.html", context)





@login_required
def admin_users(request):

    if not request.user.is_superuser:
        return redirect("accounts:login")

    clients = User.objects.filter(role="client")
    freelancers = User.objects.filter(role="freelancer")
    projects = Project.objects.all()

    context = {
        "clients": clients,
        "freelancers": freelancers,

        "client_count": clients.count(),
        "freelancer_count": freelancers.count(),
        "project_count": projects.count(),
        "total_count": clients.count() + freelancers.count(),
    }

    return render(request, "admin/users.html", context)



def manage_users(request):
    clients = User.objects.filter(role="client")
    freelancers = User.objects.filter(role="freelancer")
    projects = Project.objects.all()

    context = {
        "clients": clients,
        "freelancers": freelancers,
        "client_count": clients.count(),
        "freelancer_count": freelancers.count(),
        "total_count": clients.count() + freelancers.count(),
        "project_count": projects.count(),
    }
    return render(request, "admin/manage_users.html", context)



# accounts/views.py
from django.shortcuts import redirect

@login_required
def redirect_dashboard(request):
    return get_user_dashboard_redirect(request.user)







from django.shortcuts import get_object_or_404, redirect

from .models import Connection



from django.shortcuts import render, redirect, get_object_or_404
from .views_notifications import mark_notifications_read
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import ConnectionRequest

User = get_user_model()

@login_required
def send_connection_request(request, user_id):

    receiver = get_object_or_404(User, id=user_id)

    # prevent self follow
    if request.user == receiver:
        return redirect(request.META.get("HTTP_REFERER") or "/")

    # already requested
    already_requested = ConnectionRequest.objects.filter(
        sender=request.user,
        receiver=receiver
    ).exists()

    # already following
    already_connected = Connection.objects.filter(
        sender=request.user,
        receiver=receiver
    ).exists()

    if not already_requested and not already_connected:

        ConnectionRequest.objects.create(
            sender=request.user,
            receiver=receiver
        )
        
        from accounts.models import Notification
        from django.urls import reverse
        Notification.objects.create(
            user=receiver,
            notification_type='connection_request',
            message=f"{request.user.username} sent you a connection request.",
            link=reverse('accounts:pending_requests')
        )

    return redirect(request.META.get("HTTP_REFERER") or "/")


@login_required
def remove_connection(request, user_id):

    receiver = get_object_or_404(User, id=user_id)

    ConnectionRequest.objects.filter(
        sender=request.user,
        receiver=receiver
    ).delete()

    return redirect(request.META.get("HTTP_REFERER") or "/")


@login_required
def accept_connection_request(request, request_id):

    connection_request = get_object_or_404(
        ConnectionRequest,
        id=request_id,
        receiver=request.user
    )

    # create real connection
    Connection.objects.get_or_create(
        sender=connection_request.sender,
        receiver=connection_request.receiver
    )

    # delete request
    connection_request.delete()

    return redirect(request.META.get('HTTP_REFERER') or '/')

@login_required
def remove_connection(request, user_id):

    Connection.objects.filter(
        sender=request.user,
        receiver_id=user_id
    ).delete()

    Connection.objects.filter(
        sender_id=user_id,
        receiver=request.user
    ).delete()

    return redirect(request.META.get('HTTP_REFERER') or '/')



@login_required
def reject_connection_request(request, request_id):

    connection_request = get_object_or_404(
        ConnectionRequest,
        id=request_id,
        receiver=request.user
    )

    connection_request.delete()

    return redirect(request.META.get('HTTP_REFERER') or '/')



@login_required
def followers_list(request):

    connections = Connection.objects.filter(
        receiver=request.user
    ).select_related('sender')

    followers = []

    for connection in connections:

        follower = connection.sender
        follower.followed_date = connection.created_at

        # check if current user follows back
        is_following_back = Connection.objects.filter(
            sender=request.user,
            receiver=follower
        ).exists()
        
        is_requested_back = ConnectionRequest.objects.filter(
            sender=request.user,
            receiver=follower
        ).exists()

        follower.is_following_back = is_following_back
        follower.is_requested_back = is_requested_back
        follower.followers_count = follower.followers.count()
        follower.following_count = follower.following.count()

        followers.append(follower)

    return render(request, "accounts/followers.html", {
        "followers": followers
    })
@login_required
def following_list(request):

    connections = Connection.objects.filter(
        sender=request.user
    ).select_related('receiver')

    following_users = []

    for connection in connections:
        user = connection.receiver

        # attach followed date dynamically
        user.followed_date = connection.created_at   # use your actual field name
        user.followers_count = user.followers.count()
        user.following_count = user.following.count()

        following_users.append(user)

    return render(request, "accounts/following.html", {
        "following": following_users
    })

@login_required
def pending_requests(request):
    requests = ConnectionRequest.objects.filter(
        receiver=request.user
    )

    return render(request, "accounts/pending_requests.html", {
        "requests": requests
    })
@login_required
def find_connections(request):
    users = User.objects.exclude(id=request.user.id)
    
    for user in users:
        is_connected = Connection.objects.filter(
            sender=request.user, receiver=user
        ).exists()
        
        if is_connected:
            user.connection_status = 'connected'
        else:
            req = ConnectionRequest.objects.filter(
                sender=request.user, receiver=user
            ).order_by('-created_at').first()
            if req:
                user.connection_status = req.status
            else:
                user.connection_status = 'none'

    return render(request, "accounts/find_connections.html", {
        "users": users
    })

from accounts.decorators import admin_required

@admin_required
def admin_connection_requests(request):
    requests = ConnectionRequest.objects.filter(receiver=request.user).order_by('-created_at')
    return render(request, "admin/connection_requests.html", {"requests": requests})

@admin_required
def admin_accept_request(request, request_id):
    connection_request = get_object_or_404(ConnectionRequest, id=request_id, receiver=request.user)
    connection_request.status = 'accepted'
    connection_request.save()
    
    Connection.objects.get_or_create(
        sender=connection_request.sender,
        receiver=connection_request.receiver
    )
    return redirect('accounts:admin_connection_requests')

@admin_required
def admin_reject_request(request, request_id):
    connection_request = get_object_or_404(ConnectionRequest, id=request_id, receiver=request.user)
    connection_request.status = 'rejected'
    connection_request.save()
    return redirect('accounts:admin_connection_requests')



@login_required
def my_profile(request):
    return render(request, "accounts/my_profile.html")


def view_profile(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if user.role == 'freelancer':
        return redirect('freelancer:freelancer_profile', freelancer_id=user.id)

    from client.models import ClientProfile
    from projects.models import Job
    from accounts.models import Connection, ConnectionRequest
    from payments.models import Payment
    from proposals.models import Proposal
    from django.db.models import Sum

    profile, _ = ClientProfile.objects.get_or_create(user=user)

    # Active and total jobs posted by client
    jobs = list(Job.objects.filter(client=user).order_by('-created_at'))
    for job in jobs:
        job.proposals_count = job.job_proposals.count()
        if job.skills:
            job.skill_list = [s.strip() for s in job.skills.split(',') if s.strip()]
        else:
            job.skill_list = []

    total_jobs = len(jobs)

    # Financial and hire stats
    total_spent_val = Payment.objects.filter(client=user, status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    total_spent = f"{total_spent_val:,.2f}"
    total_hires = Payment.objects.filter(client=user, status='completed').values('freelancer').distinct().count()

    # Followers & Following
    followers_count = Connection.objects.filter(receiver=user).count()
    following_count = Connection.objects.filter(sender=user).count()

    # Viewer relationships
    is_owner = bool(request.user.is_authenticated and request.user.id == user.id)
    is_connected = False
    is_requested = False
    applied_job_ids = []

    if request.user.is_authenticated and not is_owner:
        is_connected = Connection.objects.filter(sender=request.user, receiver=user).exists()
        is_requested = ConnectionRequest.objects.filter(sender=request.user, receiver=user, status='pending').exists()
        if getattr(request.user, 'role', '') == 'freelancer':
            applied_job_ids = list(
                Proposal.objects.filter(freelancer=request.user, job__client=user).values_list('job_id', flat=True)
            )

    return render(request, "accounts/view_profile.html", {
        "profile_user": user,
        "profile": profile,
        "jobs": jobs,
        "total_jobs": total_jobs,
        "total_spent_val": total_spent_val,
        "total_spent": total_spent,
        "total_hires": total_hires,
        "followers_count": followers_count,
        "following_count": following_count,
        "is_owner": is_owner,
        "is_connected": is_connected,
        "is_requested": is_requested,
        "applied_job_ids": applied_job_ids,
    })



@login_required
def remove_follower(request, follower_id):

    follower = get_object_or_404(User, id=follower_id)

    Connection.objects.filter(
        sender=follower,
        receiver=request.user
    ).delete()

    return redirect('accounts:followers')


def testimonials_view(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to submit a testimonial.")
            return redirect("accounts:login")

        # Check if this user has already submitted a testimonial
        has_existing = Testimonial.objects.filter(user=request.user).exists() or \
                       Testimonial.objects.filter(name=request.user.username).exists() or \
                       (request.user.get_full_name() and Testimonial.objects.filter(name=request.user.get_full_name()).exists())
        if has_existing:
            messages.warning(request, "You have already shared a testimonial. Each member can only submit one testimonial.")
            return redirect("accounts:testimonials")

        # Name and role are strictly locked to the authenticated user's account
        name = request.user.get_full_name() or request.user.username
        if hasattr(request.user, "role") and request.user.role:
            role = request.user.role.capitalize()
        elif request.user.is_superuser or request.user.is_staff:
            role = "Admin"
        else:
            role = "Client"

        message_text = request.POST.get("message", "").strip()
        if not message_text:
            messages.error(request, "Please write your testimonial before submitting.")
            return redirect("accounts:testimonials")

        rating_val = request.POST.get("rating", "").strip()
        try:
            rating = int(rating_val)
            if rating < 1 or rating > 5:
                rating = 5
        except (ValueError, TypeError):
            rating = 5

        Testimonial.objects.create(
            user=request.user,
            name=name,
            role=role,
            rating=rating,
            message=message_text,
            available_connects=80,
            used_connects=20,
        )
        messages.success(request, "Thank you! Your testimonial has been shared successfully.")
        return redirect("accounts:testimonials")

    testimonials = Testimonial.objects.all().order_by("-id")

    default_name = ""
    default_role = "Client"
    user_testimonial = None
    user_has_testimonial = False

    if request.user.is_authenticated:
        default_name = request.user.get_full_name() or request.user.username
        if hasattr(request.user, "role") and request.user.role:
            default_role = request.user.role.capitalize()

        # Check if user already submitted
        user_testimonial = Testimonial.objects.filter(user=request.user).first()
        if not user_testimonial:
            user_testimonial = Testimonial.objects.filter(name=request.user.username).first()
            if not user_testimonial and request.user.get_full_name():
                user_testimonial = Testimonial.objects.filter(name=request.user.get_full_name()).first()
            if user_testimonial and not user_testimonial.user:
                user_testimonial.user = request.user
                user_testimonial.save()
        
        user_has_testimonial = user_testimonial is not None

    return render(
        request,
        "accounts/testimonials.html",
        {
            "testimonials": testimonials,
            "default_name": default_name,
            "default_role": default_role,
            "user_has_testimonial": user_has_testimonial,
            "user_testimonial": user_testimonial,
        },
    )