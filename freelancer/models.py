from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Project(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    budget = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class FreelancerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # BASIC INFO
    profile_picture = models.URLField(blank=True, null=True)
    title = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)

    # PROFESSIONAL DETAILS
    experience_level = models.CharField(max_length=50, choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('expert', 'Expert'),
    ], blank=True)

    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    # SKILLS (like Upwork tags)
    skills = models.TextField(blank=True, help_text="Comma separated skills")

    # EDUCATION
    education = models.TextField(blank=True)

    # EXPERIENCE
    work_experience = models.TextField(blank=True)

    # PORTFOLIO
    portfolio_link = models.URLField(blank=True)
    github_link = models.URLField(blank=True)

    # SOCIAL
    linkedin = models.URLField(blank=True)

    # LOCATION
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    # AVAILABILITY
    is_available = models.BooleanField(default=True)

    # COMPLETION FLAGS (for skip logic)
    is_basic_completed = models.BooleanField(default=False)
    is_professional_completed = models.BooleanField(default=False)
    is_portfolio_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username