
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
from .models import EmailOTP
from .utils import send_portal_email
from freelancer.models import FreelancerProfile

User = get_user_model()

def register(request, role=None):
    if request.method == "POST":
        email = request.POST.get("email")
        username = request.POST.get("username")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        role = request.POST.get("role")

        user = User.objects.create_user(
            email=email,
            username=username,
            phone=phone,
            password=password,
            role=role,
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

    return render(request, "accounts/register.html")

def verify_otp(request, user_id):
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

    role = role or request.GET.get("role")

    # If role not selected → show role selection page
    if not role:
        return render(request, "accounts/select_role.html")

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")

        # Uniqueness checks
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect(request.path + f"?role={role}")

        if User.objects.filter(phone=phone).exists():
            messages.error(request, "Phone already registered.")
            return redirect(request.path + f"?role={role}")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect(request.path + f"?role={role}")

        # Create user (inactive until activation)
        user = User.objects.create_user(
            username=username,
            email=email,
            phone=phone,
            password=password,
            role=role,
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

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        user = None

        # Try login using EMAIL (normal users)
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            pass

        # ✅ Try login using USERNAME (for admin)
        if user is None:
            user = authenticate(request, username=email, password=password)

        if user is not None:

            if not user.is_active:
                messages.error(request, "Activate your account first.")
                return redirect("accounts:login")

            login(request, user)

            if user.is_superuser:
                return redirect("accounts:admin_home")

            elif user.role == "client":
                return redirect("client:client_home")

            elif user.role == "freelancer":
                return redirect("freelancer:freelancer_home")

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

    if role == "client":
        if request.user.role == "client":
            return redirect("client:client_dashboard")
        else:
            return redirect("accounts:select_role")

    elif role == "freelancer":
        if request.user.role == "freelancer":
            return redirect("freelancer:freelancer_dashboard")
        else:
            return redirect("accounts:select_role")




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
    user = request.user

    if user.is_superuser:
        return redirect('/admin/')

    elif getattr(user, 'role', None) == "client":
        return redirect('client:client_home')

    elif getattr(user, 'role', None) == "freelancer":
        return redirect('freelancer:freelancer_home')

    return redirect('/')







from django.shortcuts import get_object_or_404, redirect

from .models import Connection



from django.shortcuts import redirect, get_object_or_404
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
    )

    followers = []

    for connection in connections:

        follower = connection.sender

        # check if current user follows back
        is_following_back = Connection.objects.filter(
            sender=request.user,
            receiver=follower
        ).exists()

        follower.is_following_back = is_following_back

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

    return render(request, "accounts/find_connections.html", {
        "users": users
    })




@login_required
def my_profile(request):
    return render(request, "accounts/my_profile.html")


def view_profile(request, user_id):

    user = get_object_or_404(User, id=user_id)

    profile = FreelancerProfile.objects.filter(
        user=user
    ).first()

    return render(request, "accounts/view_profile.html", {
        "profile_user": user,
        "profile": profile,
    })



@login_required
def remove_follower(request, follower_id):

    follower = get_object_or_404(User, id=follower_id)

    Connection.objects.filter(
        sender=follower,
        receiver=request.user
    ).delete()

    return redirect('accounts:followers')