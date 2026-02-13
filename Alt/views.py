import asyncio
from decimal import Decimal
import uuid
import logging
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from channels.layers import get_channel_layer

from api.point_system import record_user_action
from api.serializers import UserActionSerializer
from .models import Category, Mockup, Shirt, Atrocity, NonProfit, Order, OrderItem, CheckoutAddress
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.mail import send_mail

from api.models import Balance, Donation, Donor, User, UserProfile
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.admin.views.decorators import staff_member_required
from api.consumers import RewardConsumer
from .forms import CheckoutForm, DonorForm
from django.conf import settings
import stripe
from django.http import JsonResponse
import json


def home(request):
  return render (request, 'landing.html')


class UserDetailView(DetailView):
  model = UserProfile



  def get_object(self, queryset=None):

    return self.model.objects.filter(slug='slug')

  def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)
        context['shirt_list'] = Shirt.objects.all()
        context['atrocity_list']= Atrocity.objects.all()
        context['nonProfit_list'] = NonProfit.objects.all()
        context['slug'] = 'slug'

        return context


def dontation_page(request, slug):
  user = get_object_or_404(UserProfile, slug =slug)
  return render (request, 'user.html', {'user':user})


class ShirtList(ListView):
  model = Shirt
  template_name = 'allshirts_list.html'


def view_shirt(request, slug):
    shirt = get_object_or_404(Shirt, slug=slug)
    return render(request, 'shirt.html',{'shirt':shirt} )


@login_required
def add_to_cart(request, slug) :
  shirt = get_object_or_404(Shirt, slug = slug )
  order_item, created = OrderItem.objects.get_or_create(
    shirt=shirt,
    user = request.User,
    ordered = False
    )
  order_qs = Order.objects.filter(user=request.User, ordered= False)

  if order_qs.exists():
    order = order_qs[0]

    if order.items.filter(item__pk = shirt.pk).exists():
      order_item.quantity += 1
      order_item.save()
      messages.info(request, "Added quantity Item")
      return redirect("Alt:shirts", slug = slug)
    else:
      order.items.add(order_item)
      messages.info(request, "Item added to your cart")
      return redirect("Alt:shirts", slug = slug)
  else:
    ordered_date = timezone.now()
    order = Order.objects.create(user=request.User, ordered_date = ordered_date)
    order.items.add(order_item)
    messages.info(request, "Item added to your cart")
    return redirect("Alt:shirts", slug = slug)

@login_required
def remove_from_cart(request, slug):
    shirt = get_object_or_404(Shirt, slug=slug )
    order_qs = Order.objects.filter(
        user=request.User,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(shirt__slug=shirt.slug).exists():
            order_item = OrderItem.objects.filter(
                shirt=shirt,
                user=request.User,
                ordered=False
            )[0]
            order_item.delete()
            messages.info(request, "Item \""+order_item.ordered_shirt.name+"\" remove from your cart")
            return redirect("Alt:shirts", slug = slug)
        else:
            messages.info(request, "This Item not in your cart")
            return redirect("Alt:shirts", slug=slug)
    else:
        #add message doesnt have order
        messages.info(request, "You do not have an Order")
        return redirect("Alt:shirts", slug = slug)

class NonProfitList(ListView):
  model = NonProfit
  template_name = 'nonprofit_list.html'


def view_nonProfit(request, slug):
  nonprofit = get_object_or_404(NonProfit, slug=slug)
  return render(request,'nonprofit.html', {'nonprofit':nonprofit} )


class OrderSummaryView(LoginRequiredMixin, View):
  def get(self, *args, **kwargs):

    try:
      order = Order.objects.get(user=self.request.User, ordered =False)
      context={
        'object':order
      }
      return render(self.request, 'order_summary.html', context)
    except ObjectDoesNotExist:
      messages.error(self.request, 'You do not have an order')
      return redirect ('/')


@login_required
def reduce_quantity_from_cart(request, slug):
  shirt = get_object_or_404(Shirt, slug=slug)
  order_qs = Order.objects.filter(
    user = request.User,
    ordered = False
  )
  if order_qs.exists():
    order = order_qs[0]
    if order.shirts.filter(shirt__slug=shirt.slug).exists():
      ordered_shirt = OrderItem.objects.filter(
        ordered_shirt = shirt,
        user = request.User,
        ordered = False
      )[0]
      if ordered_shirt.qauntity > 1:
        ordered_shirt.quantity -=1
        ordered_shirt.save
      else:
        ordered_shirt.delete()
      messages.info(request, 'Item quantity has been updated')
      return redirect('Alt:order-summary')
    else:
      messages.info(request, 'This item is not in your cart')
      return redirect("Alt:order-summary")
  else:
    messages.info(request, "You have not started an order")
    return redirect("Allt:order-summary")

@staff_member_required
def verify_mockup(request, mockup_id):
    mockup = get_object_or_404(Mockup, pk=mockup_id)
    mockup.verified = True
    mockup.save()
    messages.success(request, 'Mockup verified successfully.')
    return HttpResponseRedirect(reverse('admin:Alt_mockup_changelist'))
class CheckoutView(View):
    def get(self, *args, **kwargs):
        form = CheckoutForm()
        context = {
            'form': form
        }
        return render(self.request, 'checkout.html', context)

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)

        try:
            order = Order.objects.get(user=self.request.User, ordered=False)
            if form.is_valid():
                street_address = form.cleaned_data.get('street_address')
                apartment_address = form.cleaned_data.get('apartment_address')
                country = form.cleaned_data.get('country')
                zip = form.cleaned_data.get('zip')
                same_billing_address = form.cleaned_data.get('same_billing_address')
                save_info = form.cleaned_data.get('save_info')
                payment_option = form.cleaned_data.get('payment_option')

                checkout_address = CheckoutAddress(
                    user= self.request.User,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    zip=zip
                )
                checkout_address.save()
                order.checkout_address = checkout_address
                order.save()
                return redirect('Alt:checkout')
            messages.warning(self.request, "Failed Chekout")
            return redirect('Alt:checkout')

        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an order")
            return redirect("Alt:order-summary")


def donation_form(request, slug):
    # Render the form template with the form
    stripe.api_key = settings.STRIPE_SECRET_KEY
    categories = Category.objects.all() 
    # Fetch all categories from the database
    context = {"slug": slug, "categories": categories, "stripe_publishable_key": stripe.api_key}
    return render(
        request, "donation_form.html", context
    )


def donation_page(request, slug):

    user = get_object_or_404(UserProfile, slug=slug)
    return render(request, "user.html", {"user": user})


def send_welcome_email(donor):
    subject = "Thank you for your donation!"

    donor_code_message = ""
    if donor.donor_code:
      donor_code_message = f"\nYour donor code is: {donor.donor_code}. Please keep this code for your records."
    message = f"Dear {donor.first_name},\n\nThank you for your generous donation of ${donor.amount_donated}! We greatly appreciate your support.{donor_code_message}\n\nSincerely,\nThe Donation Team"
    sender_email = "your-email@example.com"  # Change this to your email address
    recipient_email = donor.email

    send_mail(subject, message, sender_email, [recipient_email])

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


def confirmation_view(request):
    return render(request, "confirmation_page.html")


@csrf_exempt
def process_payment_made_by_outside_donor(request):
    if request.method == "POST":

        consumer = RewardConsumer()
        data = json.loads(request.body)

        token = data.get("token")
        email = data.get("email")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        amount_donated = data.get("amount_donated")
        slug = data.get("slug")  # If you're expecting 'slug' in the payload

        user = get_object_or_404(UserProfile, slug=slug)

        # Create donor object

        # Create Stripe payment
        print(amount_donated)
        try:
            charge = stripe.Charge.create(
                amount=int(float(amount_donated) * 100),  # Convert to cents
                currency="usd",
                description="Donation",
                source=token,
                metadata={
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                },
            )
            print("Stripe charge created successfully: %s", charge.id)

            donor = Donor.objects.create(
                  email=email,
                  first_name=first_name,
                  last_name=last_name,
                  amount_donated=amount_donated,
                  sent_to=user,
                  stripe_charge_id=charge.id,
              )
            
            if float(amount_donated)>= 25:
                donor_code = "altrue" + str(uuid.uuid4())[:12]
                donor.donor_code = donor_code
                print("Donor code generated: %s", donor_code)

                if donor_code is not None:
                  donor.save()
                  print('a big donation')
            
            actions = record_user_action(user,'receiveSupport', {"donation":''})
            serialized_acitons = UserActionSerializer(actions, many=True).data
            print({'the_actions:':serialized_acitons})
            channel_layer= get_channel_layer()
            async_to_sync(channel_layer.group_send)(
               f'userprofile_{user.pk}',
               {
                  'type':'send_reward_update',
                  'action_data':serialized_acitons
               }
            )

            if float(amount_donated) >= 10:
                print('over10')
                actions = record_user_action(user, 'receivedOver10', {"donation":'hey'})
                serialized_acitons = UserActionSerializer(actions, many=True).data
                
            if float(amount_donated) >= 100:
                print('over100')
                record_user_action(user, 'receiveOver100', {"donation": "donor_code"})
                serialized_acitons = UserActionSerializer(actions, many=True).data
                
            send_welcome_email(donor)
            logger.info("Welcome email sent to donor: %s", donor.email)

            return JsonResponse(
                {
                    "success": True,
                    "redirect_url": reverse("Alt:confirmation"),
                    "show_donor_code": donor.donor_code is not None,
                }
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"error": "Invalid request method"})
    # Invalid request method, return a JSON response with error
