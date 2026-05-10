
from django.contrib import admin
from .models import User
from accounts.models import ContactMessage
from .models import Testimonial

admin.site.register(User)
admin.site.register(ContactMessage)
admin.site.register(Testimonial)