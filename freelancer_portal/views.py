from django.shortcuts import render

def home(request):
    context = {}

    if request.user.is_authenticated:
        context["role"] = request.user.role
    else:
        context["role"] = "public"

    return render(request, "home/index.html", context)


def how_it_works(request):
    return render(request, "how_it_works.html")

def Terms(request):
    return render(request, "footers_file/terms.html")

def privacy_policy(request):
    return render(request, "footers_file/privacy_policy.html")




def about_us(request):
    return render(request, "footers_file/about_us.html")


from django.shortcuts import render
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings

from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render
from django.contrib import messages


def contact(request):

    if request.method == "POST":

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        # Message sent to ADMIN
        admin_message = f"""
New Contact Message

Name: {first_name} {last_name}
Email: {email}
Phone: {phone}
Subject: {subject}

Message:
{message}
"""

        send_mail(
            f"New Contact Form: {subject}",
            admin_message,
            settings.EMAIL_HOST_USER,
            ["sujanshettySK28@gmail.com"],  # admin email
            fail_silently=False,
        )

        # Confirmation message sent to USER
        user_message = f"""
Hello {first_name},

Thank you for contacting Freelancer Portal.

We received your message and our team will respond soon.

Your Message:
{message}

Regards,
Freelancer Portal Team
"""

        send_mail(
            "Message Received - Freelancer Portal",
            user_message,
            settings.EMAIL_HOST_USER,
            [email],  # user's email
            fail_silently=False,
        )

        messages.success(request, "Your message has been sent successfully!")

    return render(request, "footers_file/contact.html")