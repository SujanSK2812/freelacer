from django.urls import path
from .views import register, verify_otp, user_login, select_role,logout_view,activate_account
from . import views
urlpatterns = [
    path('register/', views.select_role, name='select_role'),
    path('activate/<uidb64>/<token>/', activate_account, name='activate'),
    path('verify/<int:user_id>/', verify_otp, name='verify_otp'),
    path('login/', user_login, name='login'),
    path('logout/', logout_view, name='logout'),
    path("password-reset/", views.password_reset_request, name="password-reset"),
    path("register/<str:role>/", views.register, name="register-role"),
]