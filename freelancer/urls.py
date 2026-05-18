from django.urls import path
from .views import freelancer_dashboard
from . import views


app_name = "freelancer"
urlpatterns = [
    path("home/", views.freelancer_home, name="freelancer_home"),
    path("dashboard/", views.freelancer_dashboard, name="freelancer_dashboard"),
    path('search/', views.search_results, name='search_results'),
    path('create_profile/', views.create_profile, name='create_profile'),
    path('my-proposals/', views.my_proposals, name='my_proposals'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path( "profile/<int:freelancer_id>/", views.freelancer_profile, name="freelancer_profile"),
    path('connections/',views.freelancer_connections,name='freelancer_connections'),
]