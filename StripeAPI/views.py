from django.conf import settings # new
from django.http.response import JsonResponse # new
from django.views.decorators.csrf import csrf_exempt # new
from django.views.generic.base import TemplateView
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework.decorators import api_view

from rest_framework import viewsets, generics, status
import stripe
import config.settings



stripe.api_key = settings.STRIPE_SECRET_KEY


class stripe_checkout(TemplateView):
  template_name= 'home.html'




@csrf_exempt
def stripe_config(request):
  if request.method == 'GET':
    stripe_config = {'publicKey': settings.STRIPE_PUBLISHABLE_KEY}
    return JsonResponse(stripe_config, safe=False)


@csrf_exempt
def create_checkout_session(request ):
  if request.method =='GET':
    domain_url = 'http://localhost:8000/'
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
      checkout_session = stripe.checkout.Session.create(
        success_url = domain_url + 'success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=domain_url + 'cancelled/', 
        payment_method_types=['card'],
        mode = 'payment',
        line_items=[
          {
            'name':'T-Shirt',
            'quantity': 1,
            'currency':'usd',
            'amount': '2000',

          }
        ]
      )
      return JsonResponse({'sessionId': checkout_session['id']})
    except Exception as e:
      return JsonResponse({'error':str(e)})



class SuccessView(TemplateView):
  template_name = 'success.html'


class CancelledView(TemplateView):
  template_name ='cancelled.html'




def stripe_webhook(request):
  stripe.api_key= settings.STRIPE_SECRET_KEY
  endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
  payload = request.body
  sig_header= request.META['HTTP_STRIPE_SIGNATURE']
  event = None


  try:
    event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
  except ValueError as e:
    return HttpResponse(status=400)
  except stripe.error.SignatureVerificationError as e:
    return HttpResponse(status = 400)

  if event['type'] == 'checkout.session.completed':
    print("Payment was successful")

  return HttpResponse(status=200)



@api_view(['POST'])
def test_payment(request):

  test_payment_intent = stripe.PaymentIntent.create(
    amount=1000, currency='pln', 
    payment_method_types=['card'],
    receipt_email='test@example.com') 
  
  return Response(status=status.HTTP_200_OK, data=test_payment_intent)