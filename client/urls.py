from django.urls import path
from .views import client_dashboard
from . import views

urlpatterns = [
    path("client/home/", views.client_home, name="client_home"),
    path("client/dashboard/", views.client_dashboard, name="client_dashboard"),
]