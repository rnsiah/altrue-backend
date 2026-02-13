from django.urls import path
from django.views.generic.base import TemplateView

from . import views
from .views import (
    confirmation_view,
    process_payment_made_by_outside_donor,
    home,
    ShirtList,
    verify_mockup,
    view_shirt,
    NonProfitList,
    view_nonProfit,
    add_to_cart,
    remove_from_cart,
    OrderSummaryView,
    reduce_quantity_from_cart,
    CheckoutView,
    UserDetailView,
    donation_page
)

app_name = "Alt"



urlpatterns = [
    path("", home, name="landing"),
    path("allshirts", ShirtList.as_view(), name="allshirts_list"),
    # path('donate/', donation_page, name='donation_page'),
    path(
        "process_payment/",
        process_payment_made_by_outside_donor,
        name="process_payment",
        
    ),
    path("verify/<int:mockup_id>/", verify_mockup, name="Alt_verify_mockup"),
    path("true/<slug>", donation_page, name="user"),
    path(
        "true/<slug>/donate/", views.donation_form, name="donation_form"
    ),  # Ensure this line is present
        path('confirmation/', confirmation_view, name='confirmation'),

    path("shirt/<slug>/", view_shirt, name="shirt"),
    path("all_nonprofits", NonProfitList.as_view(), name="nonprofit_list"),
    path("nonprofit/<slug>", view_nonProfit, name="nonprofit"),
    path("add-to-cart/<slug>/", add_to_cart, name="add-to-cart"),
    path("remove-from-cart/<slug>/", remove_from_cart, name="remove-from-cart"),
    path("order-summary", OrderSummaryView.as_view(), name="order_summary"),
    path(
        "reduce-quantity-from-cart/<slug>/",
        reduce_quantity_from_cart,
        name="reduce-quantity-from-cart",
    ),
    path(
        "confirmation/", confirmation_view, name="confirmation"
    ),  # Render template directly,  # Update here    path("chekout", CheckoutView.as_view(), name="checkout"),
]
