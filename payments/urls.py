from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('methods/', views.payment_methods_view, name='payment_methods'),
    path('methods/add/', views.add_payment_method, name='add_payment_method'),
    path('methods/<int:method_id>/delete/', views.delete_payment_method, name='delete_payment_method'),
    path('checkout/<int:proposal_id>/', views.checkout_view, name='checkout'),
    path('receipt/<int:payment_id>/', views.payment_receipt_view, name='payment_receipt'),
    path('freelancer/history/', views.freelancer_payment_history_view, name='freelancer_payment_history'),
]