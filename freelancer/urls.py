from django.urls import path
from .views import freelancer_dashboard
from . import views
urlpatterns = [
    path("home/", views.freelancer_home, name="freelancer_home"),
    path("dashboard/", views.freelancer_dashboard, name="freelancer_dashboard"),
]