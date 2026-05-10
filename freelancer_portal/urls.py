"""
URL configuration for freelancer_portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from .views import home
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('accounts/', include('accounts.urls')),
    path('client/', include('client.urls')),
    path('freelancer/', include('freelancer.urls')),
    path('projects/', include('projects.urls')),
    path("how-it-works/", views.how_it_works, name="how_it_works"),
    path("Terms/", views.Terms, name="Terms"),
    path("rivacy_policy/", views.privacy_policy, name="privacy_policy"),
    path("contact/", views.contact, name="contact"),
    path("about_us/", views.about_us, name="about_us"),
    path("how_to_find_work/", views.how_to_find_work, name="how_to_find_work"),
    path("freelancer_tips/", views.freelancer_tips, name="freelancer_tips"),
    path('messages/', include('messages_app.urls')),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )