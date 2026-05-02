from django.urls import path

from . import views
urlpatterns = [
    path('register/', views.select_role, name='select_role'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),
    path('verify/<int:user_id>/', views.verify_otp, name='verify_otp'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path("password-reset/", views.password_reset_request, name="password-reset"),
    path("register/<str:role>/", views.register, name="register-role"),
    path('role-redirect/<str:role>/', views.role_redirect, name='role_redirect'),
    path("admin-home/", views.admin_home, name="admin_home"),
    path("admin/users/", views.admin_users, name="admin_users"),
    path('dashboard/', views.redirect_dashboard, name='dashboard'),
   
]