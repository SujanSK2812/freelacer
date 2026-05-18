from django import forms
from .models import FreelancerProfile


class FreelancerProfileForm(forms.ModelForm):
    class Meta:
        model = FreelancerProfile
        exclude = [
            "user",
            "is_available",
            "is_basic_completed",
            "is_professional_completed",
            "is_portfolio_completed",
            "created_at",
        ]
        fields = [
            "profile_picture",
            "title",
            "bio",
            "experience_level",
            "hourly_rate",
            "skills",
            "education",
            "work_experience",
            "portfolio_link",
            "github_link",
            "linkedin",
            "country",
            "city",
        ]
