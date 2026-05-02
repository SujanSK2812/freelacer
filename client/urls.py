from django.urls import path
from .views import client_dashboard
from . import views

app_name = "client"

urlpatterns = [
    path("client/home/", views.client_home, name="client_home"),
    path("client/dashboard/", views.client_dashboard, name="client_dashboard"),
    path('create-job/', views.create_job, name='create_job'),
]