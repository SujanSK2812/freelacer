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
    path('freelancer/payout-detail/update/', views.freelancer_payment_history_view, name='update_freelancer_payout_detail'),
    path('contractor-payouts/', views.admin_contractor_payout_view, name='admin_contractor_payouts'),
    path('contractor-payouts/payout/', views.admin_contractor_payout_view, name='contractor_payouts'),
    path('contractor-payouts/api/freelancer/<int:freelancer_id>/', views.freelancer_payout_info_api, name='freelancer_payout_info_api'),
    path('contractor-payouts/receipt/<str:transaction_id>/', views.contractor_payout_receipt_view, name='contractor_payout_receipt'),
    path('contractor-payouts/delete/<int:payout_id>/', views.delete_contractor_payout, name='delete_contractor_payout'),
]