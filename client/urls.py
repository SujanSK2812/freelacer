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
    path("profile/", views.client_profile, name="client_profile"),
    path("edit-profile/", views.edit_client_profile, name="edit_client_profile"),
    path('proposals/', views.client_proposals, name='client_proposals'),
    path('delete-job/<int:job_id>/', views.delete_job, name='delete_job'),
    path('proposals/<int:proposal_id>/accept/', views.accept_proposal, name='accept_proposal'),
    path('proposals/<int:proposal_id>/reject/', views.reject_proposal, name='reject_proposal'),
]