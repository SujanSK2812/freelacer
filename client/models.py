from django.db import models
from django.contrib.auth import get_user_model

from freelancer_portal.upload_utils import SafeImageField, client_profile_path, client_banner_path

User = get_user_model()

class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='clientprofile')
    company_name = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    website = models.URLField(blank=True)
    profile_picture = SafeImageField(upload_to=client_profile_path, blank=True, null=True)
    banner_image = SafeImageField(upload_to=client_banner_path, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} (Client)"
