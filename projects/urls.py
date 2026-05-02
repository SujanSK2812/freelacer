from django.urls import path
from . import views
urlpatterns = [
    path('projects/', views.project_list, name='project_list'),
    path('reports/', views.reports, name='reports'),
]