
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

User = get_user_model()
def register(request):
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

        # Create activation link
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        current_site = get_current_site(request)
        activation_link = f"http://{current_site.domain}{reverse('activate', args=[uid, token])}"

        send_mail(
            "Activate Your Freelancer Portal Account",
            f"Hi {username},\n\nClick below link to activate your account:\n{activation_link}",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        # 👉 Show success page
        return render(request, "accounts/register_success.html", {
            "username": username,
            "email": email
        })

    return render(request, "accounts/register.html")
def verify_otp(request, user_id):

    user = User.objects.get(id=user_id)

    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        otp_obj = EmailOTP.objects.filter(user=user).last()

        if otp_obj and otp_obj.otp == entered_otp and otp_obj.is_valid():
            user.is_active = True
            user.save()
            otp_obj.delete()

            if user.profile.role == "client":
                return redirect("/client/dashboard/")
            else:
                return redirect("/freelancer/dashboard/")

    return render(request, "accounts/verify_otp.html")


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
        messages.success(request, "Password reset link sent to your email.")
    return render(request, "accounts/password_reset.html")





# ==========================
# REGISTER (ROLE BASED)
# ==========================
def select_role(request):

    role = request.GET.get("role")

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

        # Create activation link
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        current_site = get_current_site(request)
        activation_link = f"http://{current_site.domain}{reverse('activate', args=[uid, token])}"

        send_mail(
            "Activate Your Freelancer Portal Account",
            f"Hi {username},\n\nClick below link to activate your account:\n{activation_link}",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        # Show success page
        return render(request, "accounts/register_success.html", {
            "username": username,
            "email": email
        })

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

    return redirect("login")


# ==========================
# LOGIN
# ==========================
def user_login(request):

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:

            if not user.is_active:
                messages.error(request, "Please activate your account from email.")
                return redirect("login")

            login(request, user)

            # ROLE BASED HOME REDIRECT
            if user.role == "client":
                return redirect("/client/home/")
            else:
                return redirect("/freelancer/home/")

        else:
            messages.error(request, "Invalid email or password")

    return render(request, "accounts/login.html")


# ==========================
# LOGOUT
# ==========================
def logout_view(request):
    logout(request)
    return redirect("login")






