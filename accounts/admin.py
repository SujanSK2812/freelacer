
from django.contrib import admin
from .models import User
from accounts.models import ContactMessage


admin.site.register(User)
admin.site.register(ContactMessage)