from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random


class User(AbstractUser):

    ROLE_CHOICES = (
        ('client', 'Client'),
        ('freelancer', 'Freelancer'),
    )

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    available_connects = models.IntegerField(default=80)
    used_connects = models.IntegerField(default=20)

    is_verified = models.BooleanField(default=False)  # ✅ ADD THIS

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone']

    def __str__(self):
        return self.email

    @property
    def get_profile_picture(self):
        try:
            for prof_attr in ('freelancerprofile', 'clientprofile'):
                prof = getattr(self, prof_attr, None)
                if prof and getattr(prof, 'profile_picture', None):
                    pic = prof.profile_picture
                    pic_str = str(getattr(pic, 'name', '') or pic).strip()
                    if pic_str.startswith(('http://', 'https://')):
                        return pic_str
                    url = getattr(pic, 'url', None)
                    if url:
                        return url
        except Exception:
            pass
        return None

class EmailOTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="otps"
    )
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() <= self.created_at + timedelta(minutes=5)

    @staticmethod
    def generate_otp():
        return str(random.randint(100000, 999999))

    def __str__(self):
        return f"{self.user.email} - {self.otp}"


class Profile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    def __str__(self):
        return self.user.email
    

from django.db import models

class ContactMessage(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True)
    subject = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)





# models.py

from django.db import models

from django.core.validators import MinValueValidator, MaxValueValidator

class Testimonial(models.Model):
    ROLE_CHOICES = (
        ("Client", "Client"),
        ("Freelancer", "Freelancer"),
    )

    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    rating = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating given by the reviewer from 1 to 5 stars"
    )
    available_connects = models.IntegerField(default=80)
    used_connects = models.IntegerField(default=20)
    message = models.TextField()

    def full_stars_range(self):
        return range(self.rating)

    def empty_stars_range(self):
        return range(max(0, 5 - self.rating))

    def __str__(self):
        return f"{self.name} ({self.rating}★)"
    

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ConnectionRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_requests"
    )

    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_requests"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} -> {self.receiver} ({self.status})"


class Connection(models.Model):

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following"
    )

    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="followers"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} follows {self.receiver}"
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('proposal_view', 'Proposal View'),
        ('proposal_status', 'Proposal Status'),
        ('new_project', 'New Project'),
        ('message', 'Message'),
        ('system', 'System'),
        ('connection_request', 'Connection Request'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.is_read}"
