from django.urls import path
from .views import client_dashboard
from . import views

app_name = "client"

urlpatterns = [
    path("home/", views.client_home, name="client_home"),
    path("dashboard/", views.client_dashboard, name="client_dashboard"),
    path('create-job/', views.create_job, name='create_job'),
    path("all-freelancers/",views.all_freelancers,name="all_freelancers"),
    path("job/<int:job_id>/", views.job_detail, name="job_detail"),
]