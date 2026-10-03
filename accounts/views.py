
from django.shortcuts import render, redirect, get_object_or_404
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
from accounts.decorators import admin_required
from django.db.models import Q
from django.utils import timezone
from freelancer.models import Project
from .models import EmailOTP, Testimonial
from .utils import send_portal_email
from freelancer.models import FreelancerProfile
from projects.models import Job, JobPost

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

    # Ensure only authentication-related messages (OTP, activation, password reset, login errors) appear on the login card
    storage = messages.get_messages(request)
    auth_keywords = ('login', 'log in', 'password', 'account', 'verify', 'verified', 'otp', 'credential', 'activate', 'activation')
    auth_messages = [
        msg for msg in storage 
        if any(kw in str(msg.message).lower() for kw in auth_keywords)
    ]
    storage.used = True

    return render(request, "accounts/login.html", {"auth_messages": auth_messages})


# ==========================
# LOGOUT
# ==========================
def logout_view(request):
    storage = messages.get_messages(request)
    for _ in storage:
        pass
    storage.used = True
    logout(request)
    return redirect("home")


@login_required
def role_redirect(request, role):
    # Role comes strictly from the authenticated user's database record!
    return get_user_dashboard_redirect(request.user)




@admin_required
def admin_home(request):
    from projects.models import Job
    from payments.models import Payment
    from django.db.models import Sum

    clients = User.objects.filter(role="client")
    freelancers = User.objects.filter(role="freelancer")

    # Accurate count of real projects/jobs in the platform
    all_jobs = Job.objects.all()
    project_count = all_jobs.count()
    if Project.objects.exists():
        project_count += Project.objects.count()

    open_jobs_count = Job.objects.filter(status="open", is_active=True).count()

    # Accurate completed payment transaction volume
    volume_val = Payment.objects.filter(status="completed").aggregate(total=Sum("amount"))["total"] or 0
    if volume_val >= 1000:
        total_volume = f"₹{volume_val:,.0f}"
    else:
        total_volume = f"₹{volume_val:.0f}"

    context = {
        "client_count": clients.count(),
        "freelancer_count": freelancers.count(),
        "project_count": project_count,
        "total_count": clients.count() + freelancers.count(),
        "open_jobs_count": open_jobs_count,
        "total_volume": total_volume,
    }

    return render(request, "admin/home.html", context)


@admin_required
def admin_users(request):
    from projects.models import Job, JobPost

    clients = User.objects.filter(role="client").order_by("-date_joined")
    freelancers = User.objects.filter(role="freelancer").order_by("-date_joined")

    # Real client posted jobs/projects
    client_jobs = Job.objects.select_related("client").order_by("-created_at")

    # Freelancer talent showcases / posts
    freelancer_posts = JobPost.objects.select_related("client").filter(client__role="freelancer").order_by("-created_at")

    # Client showcases / posts
    client_posts = JobPost.objects.select_related("client").filter(client__role="client").order_by("-created_at")

    project_count = client_jobs.count()
    if Project.objects.exists():
        project_count += Project.objects.count()

    context = {
        "clients": clients,
        "freelancers": freelancers,
        "client_jobs": client_jobs,
        "freelancer_posts": freelancer_posts,
        "client_posts": client_posts,
        "projects": client_jobs,

        "client_count": clients.count(),
        "freelancer_count": freelancers.count(),
        "project_count": project_count,
        "client_jobs_count": client_jobs.count(),
        "freelancer_posts_count": freelancer_posts.count(),
        "client_posts_count": client_posts.count(),
        "total_posts_count": client_jobs.count() + freelancer_posts.count() + client_posts.count(),
        "total_count": clients.count() + freelancers.count(),
    }

    return render(request, "admin/users.html", context)


@admin_required
def admin_edit_user(request, user_id):
    if request.method == "POST":
        target_user = get_object_or_404(User, id=user_id)
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        role = request.POST.get("role", "").strip()
        is_active = request.POST.get("is_active") == "1"

        if not username or not email:
            messages.error(request, "Username and Email are required.")
            return redirect("accounts:admin_users")

        if User.objects.filter(username=username).exclude(id=target_user.id).exists():
            messages.error(request, f"Username '{username}' is already taken by another account.")
            return redirect("accounts:admin_users")

        if User.objects.filter(email__iexact=email).exclude(id=target_user.id).exists():
            messages.error(request, f"Email '{email}' is already registered to another account.")
            return redirect("accounts:admin_users")

        target_user.username = username
        target_user.email = email
        target_user.phone = phone
        if role in ["client", "freelancer"]:
            target_user.role = role
        target_user.is_active = is_active
        target_user.save()

        messages.success(request, f"User '{username}' was updated successfully.")
    return redirect("accounts:admin_users")


@admin_required
def admin_delete_user(request, user_id):
    if request.method == "POST":
        target_user = get_object_or_404(User, id=user_id)
        if target_user.id == request.user.id or target_user.is_superuser:
            messages.error(request, "Cannot delete super administrator account.")
            return redirect("accounts:admin_users")

        username = target_user.username
        target_user.delete()
        messages.success(request, f"User '{username}' was deleted successfully.")
    return redirect("accounts:admin_users")


@admin_required
def admin_delete_post(request, post_type, post_id):
    if request.method == "POST":
        from projects.models import Job, JobPost
        from freelancer.models import Project
        from freelancer_portal.upload_utils import safe_delete_unreferenced_file

        if post_type == "job":
            job = get_object_or_404(Job, id=post_id)
            title = job.title
            author = job.client.username
            img_to_delete = job.image.name if job.image else None
            poster_to_delete = job.poster.name if hasattr(job, "poster") and job.poster else None
            job.delete()
            if img_to_delete:
                safe_delete_unreferenced_file(img_to_delete)
            if poster_to_delete:
                safe_delete_unreferenced_file(poster_to_delete)
            messages.success(request, f"Client job post '{title}' by {author} was permanently deleted.")

        elif post_type in ["showcase", "post"]:
            post = get_object_or_404(JobPost, id=post_id)
            title = post.title
            author = post.client.username
            role_label = "Freelancer" if post.client.role == "freelancer" else "Client"
            img_to_delete = post.image.name if post.image else None
            poster_to_delete = post.poster.name if hasattr(post, "poster") and post.poster else None
            post.delete()
            if img_to_delete:
                safe_delete_unreferenced_file(img_to_delete)
            if poster_to_delete:
                safe_delete_unreferenced_file(poster_to_delete)
            messages.success(request, f"{role_label} post '{title}' by {author} was permanently deleted.")

        elif post_type == "project":
            proj = get_object_or_404(Project, id=post_id)
            title = proj.title
            proj.delete()
            messages.success(request, f"Project '{title}' was permanently deleted.")

        else:
            messages.error(request, "Invalid post type specified.")

    return redirect("accounts:admin_users")



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
from .views_notifications import mark_notifications_read, delete_notification, clear_all_notifications
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

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax") == "1":
        return JsonResponse({"status": "success", "message": "Connection request sent"})

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

    following_count = Connection.objects.filter(sender=request.user).count()
    return render(request, "accounts/followers.html", {
        "followers": followers,
        "following_count": following_count,
        "followers_count": len(followers),
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

    followers_count = Connection.objects.filter(receiver=request.user).count()
    return render(request, "accounts/following.html", {
        "following": following_users,
        "following_count": len(following_users),
        "followers_count": followers_count,
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
    TARGET_ORDER = [5, 6, 7, 8, 9, 10, 11, 12]
    
    METADATA = {
        'manoj_kumar': {
            'display_name': 'Manoj Kumar',
            'headline': 'Attended KVG College of Engineering (KVGC...',
            'verified': False,
            'open_to_work': False,
            'mutual_text': 'Karthik and 30 other mutual connections',
            'mutual_avatar': '/media/profiles/mutual_1.png',
            'banner_bg': 'linear-gradient(135deg, #a0b4b7 0%, #b8c8cb 100%)',
        },
        'yashas_rai': {
            'display_name': 'Yashas Rai',
            'headline': 'Student Ambassador @Google | Aspiring ...',
            'verified': True,
            'open_to_work': False,
            'mutual_text': 'Sachin and 90 other mutual connections',
            'mutual_avatar': '/media/profiles/mutual_2.png',
            'banner_bg': 'linear-gradient(135deg, #1c1c1c 0%, #2e2e2e 100%)',
        },
        'madhu_krishna': {
            'display_name': 'Madhu Krishna k',
            'headline': 'Student at KVG College of Engineering (KVGC...',
            'verified': False,
            'open_to_work': False,
            'mutual_text': 'B.N. and 37 other mutual connections',
            'mutual_avatar': '/media/profiles/mutual_3.png',
            'banner_bg': 'linear-gradient(135deg, #a0b4b7 0%, #c4d4d6 100%)',
        },
        'madesh_naik': {
            'display_name': 'Madesh Naik',
            'headline': 'Attended KVG College of Engineering (KVGC...',
            'verified': False,
            'open_to_work': True,
            'mutual_text': 'Karthik and 39 other mutual connections',
            'mutual_avatar': '/media/profiles/mutual_1.png',
            'banner_bg': 'linear-gradient(135deg, #4b382a 0%, #8c7355 100%)',
        },
        'bhanupriya': {
            'display_name': 'BS Bhanupriya',
            'headline': 'Attended KVG College of Engineering (KVGC...',
            'verified': False,
            'open_to_work': False,
            'mutual_text': 'Akshay and 1 other mutual connection',
            'mutual_avatar': '/media/profiles/mutual_1.png',
            'banner_bg': 'linear-gradient(135deg, #873e23 0%, #e76f51 100%)',
        },
        'nandan_krishna': {
            'display_name': 'Nandan Krishna K',
            'headline': 'Intern @HARMAN | Java & SQL Developer | ...',
            'verified': True,
            'open_to_work': False,
            'mutual_text': 'Rohan and 63 other mutual connections',
            'mutual_avatar': '/media/profiles/mutual_6.png',
            'banner_bg': 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
        },
        'dr_lekha': {
            'display_name': 'Dr Lekha B M',
            'headline': 'Professor KVG College of Engineering',
            'verified': False,
            'open_to_work': False,
            'mutual_text': 'Rohan and 5 other mutual connections',
            'mutual_avatar': '/media/profiles/mutual_6.png',
            'banner_bg': 'linear-gradient(135deg, #84a98c 0%, #52796f 100%)',
        },
        'manaswi_kochi': {
            'display_name': 'Manaswi Kochi',
            'headline': 'Joint Secretary – Student Council at Joi...',
            'verified': True,
            'open_to_work': True,
            'mutual_text': 'Harsha and 81 other mutual connections',
            'mutual_avatar': '/media/profiles/mutual_2.png',
            'banner_bg': 'linear-gradient(135deg, #2d6a4f 0%, #40916c 100%)',
        },
    }

    all_users = list(User.objects.exclude(id=request.user.id))
    
    def sort_key(u):
        if u.id in TARGET_ORDER:
            return (0, TARGET_ORDER.index(u.id))
        return (1, u.id)
    
    all_users.sort(key=sort_key)
    
    for user in all_users:
        is_connected = Connection.objects.filter(
            sender=request.user, receiver=user
        ).exists() or Connection.objects.filter(
            sender=user, receiver=request.user
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

        meta = METADATA.get(user.username, {})
        user.display_name = meta.get('display_name') or user.get_full_name() or user.username
        if meta.get('headline'):
            user.headline = meta['headline']
        else:
            prof = getattr(user, 'freelancerprofile', None) or getattr(user, 'clientprofile', None)
            user.headline = getattr(prof, 'title', None) or getattr(prof, 'company_name', None) or 'Professional on Network'
        
        user.is_verified_badge = meta.get('verified', user.is_verified)
        user.open_to_work = meta.get('open_to_work', False)
        user.mutual_text = meta.get('mutual_text', '12 mutual connections')
        user.mutual_avatar = meta.get('mutual_avatar', '/media/profiles/mutual_1.png')
        user.banner_bg = meta.get('banner_bg', 'linear-gradient(135deg, #a0b4b7 0%, #b8c8cb 100%)')

    college_users = [
        {
            "id": 901,
            "display_name": "Ananya Rai",
            "headline": "Student at KVG College of Engineering (KVGCE), Sullia",
            "mutual_text": "8 mutual connections",
            "mutual_avatar": "/media/profiles/mutual_1.png",
            "avatar": "/media/profiles/alumni_1.png",
            "is_verified": False,
            "open_to_work": False,
            "banner_bg": "linear-gradient(135deg, #a0b4b7 0%, #b8c8cb 100%)",
            "connection_status": "none"
        },
        {
            "id": 902,
            "display_name": "Prajwal Gowda",
            "headline": "Student at KVG College of Engineering (KVGCE)",
            "mutual_text": "14 mutual connections",
            "mutual_avatar": "/media/profiles/mutual_2.png",
            "avatar": "",
            "is_verified": False,
            "open_to_work": False,
            "banner_bg": "linear-gradient(135deg, #d8e2ec 0%, #eef2f6 100%)",
            "connection_status": "none"
        },
        {
            "id": 903,
            "display_name": "Rakshitha S",
            "headline": "Attended KVG College of Engineering",
            "mutual_text": "22 mutual connections",
            "mutual_avatar": "/media/profiles/mutual_3.png",
            "avatar": "",
            "initial": "R",
            "initial_bg": "#c2185b",
            "is_verified": False,
            "open_to_work": False,
            "banner_bg": "linear-gradient(135deg, #ccd5ae 0%, #e9edc9 100%)",
            "connection_status": "none"
        },
        {
            "id": 904,
            "display_name": "Kiran Kumar",
            "headline": "Alumni at KVG College of Engineering, Sullia",
            "mutual_text": "5 mutual connections",
            "mutual_avatar": "/media/profiles/mutual_6.png",
            "avatar": "",
            "is_verified": False,
            "open_to_work": False,
            "banner_bg": "linear-gradient(135deg, #d8e2ec 0%, #eef2f6 100%)",
            "connection_status": "none"
        }
    ]

    sent_ids = set(Connection.objects.filter(sender=request.user).values_list('receiver_id', flat=True))
    received_ids = set(Connection.objects.filter(receiver=request.user).values_list('sender_id', flat=True))
    connected_ids = (sent_ids | received_ids) - {request.user.id}
    connections_count = len(connected_ids)

    from projects.models import Job, JobPost
    if getattr(request.user, 'role', '') == 'client':
        posts_count = Job.objects.filter(client=request.user).count()
        posts_label = "My Job Posts"
    else:
        posts_count = JobPost.objects.filter(client=request.user).count()
        posts_label = "My Showcases"

    pending_requests_count = ConnectionRequest.objects.filter(receiver=request.user, status='pending').count()
    followers_count = request.user.followers.count() if hasattr(request.user, 'followers') else 0

    return render(request, "accounts/find_connections.html", {
        "users": all_users,
        "college_users": college_users,
        "connections_count": connections_count,
        "pending_requests_count": pending_requests_count,
        "followers_count": followers_count,
        "posts_count": posts_count,
        "posts_label": posts_label,
    })


@login_required
def my_connections(request):
    sent_ids = set(Connection.objects.filter(sender=request.user).values_list('receiver_id', flat=True))
    received_ids = set(Connection.objects.filter(receiver=request.user).values_list('sender_id', flat=True))
    connected_ids = (sent_ids | received_ids) - {request.user.id}
    connections_count = len(connected_ids)

    connected_users = User.objects.filter(id__in=connected_ids)

    connections_list = []
    for u in connected_users:
        conn = Connection.objects.filter(
            (Q(sender=request.user, receiver=u) | Q(sender=u, receiver=request.user))
        ).order_by('-created_at').first()

        prof = getattr(u, 'freelancerprofile', None) or getattr(u, 'clientprofile', None)
        headline = getattr(prof, 'title', None) or getattr(prof, 'company_name', None) or (u.role.title() if getattr(u, 'role', None) else 'Member')

        connections_list.append({
            'user': u,
            'headline': headline,
            'connected_at': conn.created_at if conn else None,
            'avatar': u.get_profile_picture,
            'display_name': u.get_full_name() or u.username,
        })

    # Sort recently added first
    connections_list.sort(key=lambda x: x['connected_at'] or timezone.now(), reverse=True)

    # Pending connection requests count (invitations received)
    pending_requests_count = ConnectionRequest.objects.filter(receiver=request.user, status='pending').count()

    # Following & followers count
    following_count = request.user.following.count() if hasattr(request.user, 'following') else 0
    followers_count = request.user.followers.count() if hasattr(request.user, 'followers') else 0

    # Real user post count for sidebar
    if getattr(request.user, 'role', '') == 'client':
        posts_count = Job.objects.filter(client=request.user).count()
        posts_label = "My Job Posts"
    else:
        posts_count = JobPost.objects.filter(client=request.user).count()
        posts_label = "My Showcases"

    # Real Suggested Connections (platform users not yet connected or self)
    pending_sent_ids = set(ConnectionRequest.objects.filter(sender=request.user, status='pending').values_list('receiver_id', flat=True))
    excluded_ids = connected_ids | {request.user.id}
    other_users = User.objects.exclude(id__in=excluded_ids).filter(is_active=True, role__in=['freelancer', 'client']).order_by('-date_joined')

    suggestions = []
    for u in other_users:
        prof = getattr(u, 'freelancerprofile', None) or getattr(u, 'clientprofile', None)
        headline = getattr(prof, 'title', None) or getattr(prof, 'company_name', None) or (u.role.title() if getattr(u, 'role', None) else 'Member')
        
        banner_url = None
        if hasattr(u, 'get_banner_image') and u.get_banner_image:
            banner_url = u.get_banner_image
        elif prof and getattr(prof, 'banner_image', None):
            banner_url = getattr(prof.banner_image, 'url', None)

        suggestions.append({
            'user': u,
            'display_name': u.get_full_name() or u.username,
            'headline': headline,
            'avatar': u.get_profile_picture,
            'banner_url': banner_url,
            'is_pending': u.id in pending_sent_ids,
            'role': getattr(u, 'role', ''),
        })

    return render(request, "accounts/my_connections.html", {
        "connections": connections_list,
        "connected_users": connected_users,
        "connections_count": connections_count,
        "pending_requests_count": pending_requests_count,
        "following_count": following_count,
        "followers_count": followers_count,
        "posts_count": posts_count,
        "posts_label": posts_label,
        "suggestions": suggestions,
    })


@login_required
def redirect_posts(request):
    """Redirect to the create post page based on user's role (Post Job for Client, Create Showcase for Freelancer)."""
    if getattr(request.user, 'role', '') == 'client':
        return redirect('client:create_job')
    elif getattr(request.user, 'role', '') == 'freelancer':
        return redirect('freelancer:create_showcase')
    elif request.user.is_superuser:
        return redirect('admin:index')
    return redirect('home')


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
    total_hires = Proposal.objects.filter(job__client=user, status='accepted').count()

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