from django.urls import path
from . import views

urlpatterns = [
    path('projects/', views.project_list, name='project_list'),
    path('reports/', views.reports, name='reports'),
    path('like/<int:job_id>/', views.like_job, name='like_job'),
    path('comment/<int:job_id>/', views.comment_job, name='comment_job'),
]