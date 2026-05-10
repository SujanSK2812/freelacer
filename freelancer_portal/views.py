from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from accounts.models import Testimonial
from accounts.models import ContactMessage 
from django.contrib.auth import get_user_model
from freelancer.models import Project
User = get_user_model()


User = get_user_model()

def home(request):

    testimonials = Testimonial.objects.all()

    freelancers_count = User.objects.filter(role="freelancer").count()
    clients_count = User.objects.filter(role="client").count()
    projects_count = Project.objects.count()

    context = {
        "testimonials": testimonials,

        "total_count": freelancers_count,
        "clients_count": clients_count,
        "projects_count": projects_count,
    }

    if request.user.is_authenticated:
        context["role"] = request.user.role
    else:
        context["role"] = "public"

    return render(request, "home/index.html", context)

  # import model

def contact(request):

    if request.method == "POST":

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        subject = request.POST.get("subject")
        message = request.POST.get("message")
        message_count = ContactMessage.objects.filter(email=email).count()
        if message_count >= 3:
            messages.error(request, "You have reached the maximum number of messages allowed. Please wait before sending more.")
            return render(request, "footers_file/contact.html")
        # ✅ SAVE TO DATABASE (IMPORTANT)
        ContactMessage.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            subject=subject,
            message=message,
        )

        # ✅ Email to ADMIN
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
            ["sujanshettySK28@gmail.com"],
            fail_silently=False,
        )

        # ✅ Email to USER
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
            [email],
            fail_silently=False,
        )

        messages.success(request, "Your message has been sent successfully!")

    return render(request, "footers_file/contact.html")


@login_required
def how_it_works(request):
    return render(request, "how_it_works.html")

def Terms(request):
    return render(request, "footers_file/terms.html")

def privacy_policy(request):
    return render(request, "footers_file/privacy_policy.html")

def about_us(request):
    return render(request, "footers_file/about_us.html")

def how_to_find_work(request):
    return render(request, "footers_file/how_to_find_work.html")

def freelancer_tips(request):
    return render(request, "footers_file/freelancer_tips.html")


def how_to_hire(request):
    return render(request, "footers_file/how_to_hire.html")

@login_required
def post_to_project(request):
    return render(request, "footers_file/post_to_project.html")

@login_required
def find_freelancers(request):
    return render(request, "footers_file/find_freelancers.html")


def succes_stories(request):
    return render(request, "footers_file/succes_stories.html")


