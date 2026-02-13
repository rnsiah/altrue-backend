from django.urls import path, re_path
# from django.conf.urls import url
from . import views

app_name= 'StripeAPI'


urlpatterns = [
    re_path(r'^test-payment/$', views.test_payment),
    path('stripe-checkout/', views.stripe_checkout.as_view(), name='home'),
    path('config/', views.stripe_config),
    path('create-checkout-session/', views.create_checkout_session, name ='create-checkout-session'),
    path('cancelled/', views.CancelledView.as_view(), name='cancelled'),
    path('success', views.SuccessView.as_view(), name='success'),
    path('webhook/', views.stripe_webhook),
   
    # path('create-payment-intent/', views.create_payment_intent, name='create-payment-intent'),
    # path('handle-payment-confirmation/', views.handle_payment_confirmation, name='handle-payment-confirmation'),

]