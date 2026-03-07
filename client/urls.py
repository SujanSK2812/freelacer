from django.urls import path
from .views import client_dashboard
from . import views

urlpatterns = [
    path("home/", views.client_home, name="freelancer_home"),
    path("dashboard/", views.client_dashboard, name="freelancer_dashboard"),
]