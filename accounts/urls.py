from django.urls import path
from . import views
app_name = "accounts"

urlpatterns = [
    path('register/', views.select_role, name='select_role'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),
    path('verify/<int:user_id>/', views.verify_otp, name='verify_otp'),
    path('resend-otp/<int:user_id>/', views.resend_otp, name='resend_otp'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path("password-reset/", views.password_reset_request, name="password-reset"),
    path("password-reset-confirm/<uidb64>/<token>/", views.password_reset_confirm, name="password_reset_confirm"),
    path("register/<str:role>/", views.register, name="register-role"),
    path('role-redirect/<str:role>/', views.role_redirect, name='role_redirect'),
    path("admin-home/", views.admin_home, name="admin_home"),
    path("admin/users/", views.admin_users, name="admin_users"),
    path('dashboard/', views.redirect_dashboard, name='dashboard'),
    path('connect/<int:user_id>/',views.send_connection_request,name='send_connection_request'),

    path('remove-connection/<int:user_id>/',views.remove_connection,name='remove_connection'),
    path("send-request/<int:user_id>/",views.send_connection_request,name="send_connection_request"),

    path("accept-request/<int:request_id>/",views.accept_connection_request,name="accept_connection_request"),  
    path("reject-request/<int:request_id>/",views.reject_connection_request,name="reject_connection_request"),
    path("followers/", views.followers_list, name="followers"),
    path("following/", views.following_list, name="following"),
    path("pending-requests/", views.pending_requests, name="pending_requests"),
    path("find-connections/", views.find_connections, name="find_connections"),
    path("my-profile/", views.my_profile, name="my_profile"),
    path("profile/<int:user_id>/", views.view_profile, name="view_profile"),
    path('remove-follower/<int:follower_id>/',views.remove_follower,name='remove_follower'),
]