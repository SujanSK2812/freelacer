from django.urls import path
from .views import client_dashboard
from . import views

urlpatterns = [
    path("home/", views.client_home, name="client_home"),
    path("dashboard/", views.client_dashboard, name="client_dashboard"),
]