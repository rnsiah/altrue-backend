import json
from unicodedata import category
import requests
from urllib import response
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

from django.db.models import F, Window, Sum
from django.db.models.functions import Rank
from api.point_system import record_user_action
from rest_framework.serializers import ValidationError
from django.contrib.auth.decorators import permission_required
from django.db.models.query import Prefetch
from django.forms.models import model_to_dict
from django.conf import settings
from django.utils.decorators import method_decorator
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from Alt.models import AltrueAction, AltrueLevel, Atrocity, AtrocityBalance, Category, CompanyNonProfitRelationship, CompanyStore, ForProfitCompany, NonProfit, NonProfitBalance, NonProfitProject, Order, OrderItem, Payment, PointSystemConversionRate, Quiz, QuizResult, Rating, ShareRecord, Shirt, ShirtColor, ShirtGroup, ShirtSize, ShirtVariations, UserAltrueAction
from api.models import AltruePoints, Balance, Donation, Donor, Link, PointTransaction, Post, User, UserDonation, UserProfile
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from .serializers import AltrueActionSerializer, AltrueLevelSerializer, AltrueStatisticsSerializer, CompanyMatchDonationSerializer, CompanyNonProfitRelationshipSerializer, CompanyStoreSerializer, DonationSerializer, DonorSerializer, LeaderBoardSerializer, NonProfitListSerializer, NonProfitProjectSerializer, OrderItemSerializer, PaymentSerializer, PointTransactionSerializer, PostSerializer, ProfileRepSerializer, ProjectRepSerializer, QuizResultSerializer, QuizSerializer, ShirtGroupSerializer, ShirtListSerialzier, ShirtSerializer, NonProfitSerializer, AtrocitySerializer,  CategorySerializer, RatingSerializer, ShirtSizeSerializer, ShirtVariationSerializer, UserActionSerializer, UserProfileSerializer
from api.serializers import ForProfitCompanySerializer, LinkSerializer, OrderSerializer, UserDonationSerializer, UserSerializer
from api.permissions import IsLoggedInUserOrAdmin, IsAdminUser
from django.shortcuts import get_object_or_404
from django.http.response import Http404
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from rest_framework_bulk import (
    BulkListSerializer,
    BulkSerializerMixin,
    ListBulkCreateUpdateDestroyAPIView,
)
from django.views.decorators.csrf import csrf_exempt
from requests.api import request
from rest_flex_fields import is_expanded
import stripe
from django.conf import settings

# Use environment-based Stripe key
stripe.api_key = settings.STRIPE_SECRET_KEY


class FlexFieldsMixin(object):
    permit_list_expands = []

    def get_serializer_context(self):
        default_context = super(FlexFieldsMixin, self).get_serializer_context()

        if hasattr(self, "action") and self.action == "list":
            default_context["permitted_expands"] = self.permit_list_expands

        return default_context


class FlexFieldsModelViewSet(FlexFieldsMixin, viewsets.ModelViewSet):
    pass


class UserProfileFinder(generics.RetrieveUpdateDestroyAPIView):
  serializer_class= UserProfileSerializer
  queryset= UserProfile.objects.all()


def validate_donor_code(email, code):
    try:
        return Donor.objects.get(code=code, email=email)
    except Donor.DoesNotExist:
        return None


class UserProfileView(viewsets.ModelViewSet):
    queryset=UserProfile.objects.filter()
    serializer_class = UserProfileSerializer
    authentication_classes = (TokenAuthentication, )

    @action(detail=True, methods=['patch'])
    def update_profile(self, request, *args, **kwargs):
        userprofile = self.get_object()
        serializer = UserProfileSerializer(userprofile, data=request.data, partial=True)
        if serializer.is_valid():
            donor_code = request.data.get(
                "donor_code"
            )  # Get donor code from request data

            serializer.save()

            required_fields = ['city', 'zip_code', 'dob', 'address', 'username']
            all_fields_present = all(field in request.data for field in required_fields) 

            if all_fields_present:
                has_valid_code = validate_donor_code(code = donor_code , email = userprofile.user.email)
                if has_valid_code:
                    userprofile.user.registered_with_code = True
                    userprofile.user.profile_created = True
                    userprofile.user.save()
                    return Response(serializer.data, status = status.HTTP_200_OK)
                
                    
                userprofile.user.profile_created = True
                userprofile.user.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail = True, methods=['post'])
    def addUserDonationToNonProfit(self, request, *args, **kwargs):
        userprofile = self.get_object()
        wallet = Balance.objects.get(account = userprofile)
        amount = request.data['amount']
        np = NonProfit.objects.get(slug = request.data['id'])
        donation_type = request.data['donation_type']

        stripe_customer= stripe.Customer.create(
          email= userprofile.user.email,)

        if amount != 1 and amount != 5 and amount != 10:
            metadata = {"product_id": "prod_Ps8HNJYPOSd9bz",
                        'user_id':userprofile.user.id,
                        'nonprofit_id':np.id,
                        'donation_type':donation_type,
                        'donation_category':'nonprofit'}

        print(metadata)
        try:
            intent = stripe.PaymentIntent.create(
              amount= amount,
              currency='usd',
              description='userdonation',
              customer= stripe_customer.id,
              metadata=metadata
            )

            ephemeral_key= stripe.EphemeralKey.create(
              customer= stripe_customer.id,
              stripe_version='2020-08-27'
            )
            response_data={
              'id':intent.id,
              'client_secret':intent.client_secret,
              'ephemeral_key':ephemeral_key.secret,
              'customer':stripe_customer.id,
              'metadata':metadata
            }

            UserDonation.objects.create(
                user = userprofile, 
                dollar_amount = int((amount)/100), 
                nonprofit =np, 
                stripe_id=intent.id,
                wallet =wallet,
                donation_type="S",
                )
            
            

            return Response(response_data, status=status.HTTP_200_OK)
        except stripe.error.StripeError as e:
            # Handle any Stripe errors
            return JsonResponse({"error": str(e)}, status=400)

        # newDonation = UserDonation.create(
        #     user=userprofile,
        #     wallet=wallet,
        #     amount=amount,
        #     donation_type=donation_type,
        #     nonprofit=np,
        # )
        # newDonation.save()
        # response = {"message": "You have donated ${amount} to help ${atrocity.title}"}
        # return Response(response, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def addUserDonationToAtrocity(self, request, *args, **kwargs):
        userprofile = self.get_object()
        wallet = Balance.objects.get(account = userprofile)
        amount = request.data['amount']
        atrocity = Atrocity.objects.get(pk = request.data['id'])
        donation_type = request.data['donation_type']

        stripe_customer= stripe.Customer.create(
          email= userprofile.user.email,)

        if amount != 1 and amount != 5 and amount != 10:
            metadata = {"product_id": "prod_Ps8HNJYPOSd9bz",
                        'user_id':userprofile.user.id,
                        'atrocity_id':atrocity.id,
                        'donation_type':donation_type,
                        'donation_category':'atrocity'}

        print(metadata)
        try:
            intent = stripe.PaymentIntent.create(
              amount= amount,
              currency='usd',
              description='userdonation_atrocity',
              customer= stripe_customer.id,
              metadata=metadata
            )

            ephemeral_key= stripe.EphemeralKey.create(
              customer= stripe_customer.id,
              stripe_version='2020-08-27'
            )
            response_data={
              'id':intent.id,
              'client_secret':intent.client_secret,
              'ephemeral_key':ephemeral_key.secret,
              'customer':stripe_customer.id,
              'metadata':metadata
            }

            UserDonation.objects.create(
                user = userprofile, 
                dollar_amount = int((amount)/100), 
                atrocity =atrocity,
                stripe_id=intent.id,
                wallet =wallet,
                donation_type="S",
                )
            
            record_user_action(userprofile,'makeADonation', {'amount':amount, 'atrocity_id':atrocity.id})

            return Response(response_data, status=status.HTTP_200_OK)
        except stripe.error.StripeError as e:
            # Handle any Stripe errors
            return JsonResponse({"error": str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def addUserDonationToProject(self, request, *args, **kwargs):
        profile=self.get_object()
        wallet = Balance.objects.get(account = profile)
        amount = request.data['amount']
        project = NonProfitProject.objects.get(pk= request.data['project'])

        stripe_customer=stripe.Customer.create(email = profile.user.email)
        metadata= {
        "user_id":profile.user.id,
        'project_id': project.id,
        'donation_type':"S",
        "customer":stripe_customer.id,
        'donation_category':'project'
        }

        try:
            intent = stripe.PaymentIntent.create(
                amount= amount,
                currency='usd',
                description='userdonation_project',
                customer= stripe_customer.id,
                metadata=metadata
            )

            ephemeral_key = stripe.EphemeralKey.create(
                customer=stripe_customer.id,
                stripe_version='2020-08-27'
            )

            response_data={
                'id':intent.id,
                'client_secret':intent.client_secret,
                'ephemeral_key':ephemeral_key.secret,
                'customer':stripe_customer.id,
                'metadata':metadata
            }

            UserDonation.objects.create(
                user=profile,
                dollar_amount = int(amount/100),
                project =project,
                stripe_id = intent.id,
                wallet = wallet,
                donation_type ="S"
                )
            
            record_user_action(profile, 'makeADonation', {'amount':amount, 'project_id':project.id} )

            return Response(response_data, status=status.HTTP_200_OK)
        except stripe.error.StripeError as e:

            return JsonResponse({'error':str(e)}, status =400)

    @action(detail=True, methods=["post"])
    def manageUserFollowers(self, request, *args, **kwargs):
        profile = self.get_object()
        following_list = profile.profiles_following.all()
        lo = request.data
        profile_to_follow = UserProfile.objects.get(user=request.data["id"])
        if request.data["following"] == "follow":
            try:
                if profile_to_follow not in following_list:
                    profile.profiles_following.add(profile_to_follow)
                    profile.save()
                    serialized = ProfileRepSerializer(
                        profile.profiles_following, many=True
                    )
                    response = {
                        "message": "Now Following {}".format(profile_to_follow.username)
                    }, serialized.data

                    return Response(response, status=status.HTTP_200_OK)
                else:
                    response = {"message": "You are already Following This Profile"}
                    return Response(response, status=status.HTTP_200_OK)
            except:
                response = {"message": "Something Went Wrong adding" + " " + str(lo)}
                return Response(response, status=status.HTTP_200_OK)
        elif (
            request.data["following"] == "unfollow"
            and profile_to_follow in following_list
        ):
            try:
                profile.profiles_following.remove(profile_to_follow)
                profile.save()
                serialized = ProfileRepSerializer(profile.profiles_following, many=True)
                response = {
                    "message": "You have just unfollowed {}".format(
                        profile_to_follow.username
                    ),
                }, serialized.data
                return Response(response, status =status.HTTP_201_CREATED)
            except:
                response = {'message': 'something went wrong when unfollowing user'}
        return Response(status = status.HTTP_501_NOT_IMPLEMENTED)

        # elif request.data['unfollow'] is 'unfollow':
        #   try:
        #     if profile_to_follow in following_list:
        #       profile.following.remove(profile_to_follow)
        #       profile.save()
        #       response = {'message': 'You have unfollowed ${profile_to_follow.user.}'}
        #       return Response(response, status=status.HTTP_200_OK)
        #     else:
        #       response = {'message': 'You are not Following This Profile'}
        #       return Response(response, status=status.HTTP_200_OK)
        #   except:
        #     response = {"message" :'Something Went Wrong'}
        #     return Response(response, status=status.HTTP_200_OK)

    # @action(detail = True, methods =['patch'])
    # def add_profilePic(self, request, *args, **kwargs):
    #     userprofile = self.get_object()
    #     picture  = request.data['profile_picture']
    #     userprofile.profile_picture  = picture
    #     userprofile.save(update_fields=['profile_picture'])
    #     response = {'message': 'Profile Picture has been updated', 'result': 'success'}
    #     return Response(response, status=status.HTTP_200_OK)

    @action(detail= True, methods=['patch'])
    def add_shirt(self, request, *args, **kwargs,):
        userprofile = self.get_object()
        shirt_list= userprofile.shirt_list.all()
        shirt_instance = Shirt.objects.get(slug = request.data['slug'])
        try:
            if shirt_instance in shirt_list:
                print(shirt_instance)
                response = {'message': 'This Shirt Is already In Your List','result': 'hey'}
                return Response(response, status= status.HTTP_200_OK)
            else:
                print(shirt_instance)
                userprofile.shirt_list.add(shirt_instance)
                userprofile.save()
                response= {'message': 'Shirt_List Updated', 'result':'hey'}
                return Response(response, status= status.HTTP_200_OK)
        except:
            print(shirt_instance)
            response = {'message': "Something went wrong 14", 'result': 'hey'}
            return Response(response, status=status.HTTP_200_OK)

    @action(detail =True, methods=['patch'])
    def remove_shirt(self, request, *args, **kwarsgs):
        userprofile = self.get_object()

        try:
            shirt_instance = Shirt.objects.get(id =request.data['id'])
            userprofile.shirt_list.remove(shirt_instance)
            userprofile.save()
            response ={ 'message': 'Shirt List has been update', 'result':'hey'}
            return Response(response, status= status.HTTP_200_OK)
        except:
            response = {'message': "Something went wrong 13", 'result': 'hey'}
            return Response(response, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def add_atrocity(self, request, *args, **kwargs):
        userprofile = self.get_object()
        atrocity = Atrocity.objects.get(id = request.data['id'])
        
        try:
            if atrocity not in userprofile.atrocity_list.all():
                userprofile.atrocity_list.add(atrocity)
                userprofile.save()
                record_user_action(userprofile, 'followatroc', {'atrocity_id':atrocity.id})
                response={ 'message': 'Atrocity List has been updated and you earned points', 'result': None}
                return Response(response, status= status.HTTP_200_OK)
            else:
                response =  {'message': 'This Atrocity is already in your list', 'result': None}
                return Response(response, status= status.HTTP_200_OK)
        except Exception as e:
            response = {'message': "Something went wrong 12", 'result': 'hey'}
            return Response(response, status=status.HTTP_200_OK)

    @action(detail = True, methods=['patch'])
    def remove_atrocity(self, request, *args, **kwargs):
        userprofile = self.get_object()
        atrocity_list = userprofile.atrocity_list.all()
        atrocity_instance = Atrocity.objects.get(id = request.data['id'])
        try:

            if atrocity_instance in atrocity_list:
                userprofile.atrocity_list.remove(atrocity_instance)
                userprofile.save()
                response ={ 'message': 'Atrocity List has been updated', 'result': 'hey'}
                return Response(response, status= status.HTTP_200_OK)
        except:
            response = {'message': "Something went wrong 11", 'result':'hey'}
            return Response(response, status=status.HTTP_200_OK)

    @action(detail = True, methods=['patch'])
    def add_nonprofit(self, request, *args, **kwargs):
        userprofile = self.get_object()
        nonprofit = NonProfit.objects.get(id=request.data['id'])
        
        try:
            if nonprofit not in userprofile.nonProfit_list.all():
                
                userprofile.nonProfit_list.add(nonprofit)
                userprofile.save()
                record_user_action(userprofile, 'follownp',{'nonprofit_id':nonprofit.id})
                response={ 'message': 'Nonprofit List has been updated and you earned points', 'result': None}
                return Response(response, status= status.HTTP_200_OK)
            else:
                response =  {'message': 'This NonProfit is already in your list', 'result': None}
                return Response(response, status= status.HTTP_200_OK)
        except Exception as e:
            response = {'message': "Something went wrong 12", 'result': 'hey'}
            return Response(response, status=status.HTTP_200_OK)

    
    @action(detail = True, methods=['patch'])
    def remove_nonprofit(self, request, *args, **kwargs):
        userprofile= self.get_object()
        nonprofit_list = userprofile.nonProfit_list.all()
        try:
            nonprofit_instance = NonProfit.objects.get(id = request.data['id'])
            if nonprofit_instance in nonprofit_list:
                userprofile.nonProfit_list.remove(nonprofit_instance)
                userprofile.save()
                response={ 'message': 'Nonprofit List has been update', 'result': 'hey'}
                return Response(response, status= status.HTTP_200_OK)
        except:
            response = {'message': "Something went wrong 12", 'result': 'hey'}
            return Response(response, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def add_company(self, request, *args, **kwargs):
        userprofile = self.get_object()
        company_list = userprofile.companies.all()
        try:
            company_instance = ForProfitCompany.objects.get(id = request.data['id'])
            if company_instance not in company_list:
                userprofile.companies.add(company_instance)
                userprofile.save()

                response = {'message': 'Company list has been updated', 'result': company_instance}
                return Response(response, status= status.HTTP_200_OK)
            else:
                response = {'message': 'This Company is already in your list', 'result': company_instance}
                return Response(response, status= status.HTTP_200_OK)
        except:
            response = {'message': "Something went wrong 20", 'result': 'hey'}
            return Response(response, status=status.HTTP_200_OK)

    @action(detail =True, methods=['patch'])
    def remove_company(self, request, *args, **kwargs):
        userprofile = self.get_object()
        company_list = userprofile.companies.all()
        try:
            company_instance = ForProfitCompany.objects.get(id=request.data['id'])
            if company_instance in company_list:
                userprofile.companies.remove(company_instance)
                userprofile.save()
                response = {'message':'Your company list has been updated, you have removed a company from your list', 'result':company_instance}
                return Response(response, status= status.HTTP_200_OK)
        except:
            response = {'message':'Something went wrong when updating'}
            return Response(response, status= status.HTTP_200_OK)

    @action(detail = True, methods=['patch'])
    def remove_company(self, request, *args, **kwargs):
        userprofile= self.get_object()
        company_list = userprofile.company.all()
        try:
            company_instnace = ForProfitCompany.objects.get(id = request.data['id'])
            if company_instnace in company_list:
                userprofile.company.remove(company_instnace)
                userprofile.save()
                response={ 'message': 'Nonprofit List has been update', 'result': 'hey'}
                return Response(response, status= status.HTTP_200_OK)
        except:
            response = {'message': "Something went wrong22", 'result': 'hey'}
            return Response(response, status=status.HTTP_200_OK)

    @action(detail = True, methods=['get'])
    def followerNonProfitDonations(self, request, *args, **kwargs):
        userprofile = self.get_object()
        donation_list =[]
        following_list = userprofile.following.all()
        try:
            for follower in following_list:
                nonprofit = NonProfit.objects.filter(id = request.data['id'])
                all_donations = UserDonation.objects.filter(user =follower, nonprofit = nonprofit)
                for donation in all_donations:
                    serializer = UserDonationSerializer(donation)
                    donation_list.  pend(serializer.data)
            response = {'message':'donations', 'result':donation_list}
            return Response(response, status = status.HTTP_200_OK)

        except:
            response = {'message': "Something went wron 23g", 'result': 'hey'}
            return Response(response, status=status.HTTP_200_OK)

    # response = {'message': 'Companies', 'result':serializer.data}
# class UpdaeteForProfitCompany(APIView):
#   permission_classes =(IsAuthenticated,)
#   def


class PostViewSet(viewsets.ModelViewSet):
  queryset = Post.objects.all()
  serializer_class = PostSerializer


class PaymentViewSet(viewsets.ViewSet):
    def create(self, request):
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Process the payment and address details here

        # Create a Payment instance
        payment = Payment.objects.create(**serializer.validated_data)

        return Response({'message': 'Payment details received and stored successfully'})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes =(TokenAuthentication,)


    # def get_object(self, pk):
    #     return User.objects.get(pk= request.user.id)



    def get_permissions(self):
        permission_classes = []
        if self.action == 'create':
            permission_classes = [AllowAny]
        elif self.action == 'retrieve' or self.action == 'update' or self.action == 'partial_update':
            permission_classes = [IsAuthenticated]
        elif self.action == 'list' or self.action == 'destroy':
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]


# class UserDetail(APIView):
#   permission_classes = (IsAuthenticated, )


class ForProfitCompanyAddLocation(APIView):
  authentication_classes = (TokenAuthentication, )

  def get_object(self, pk):
    try:
      return ForProfitCompany.objects.get(pk=pk)
    except ForProfitCompany.DoesNotExist:
      raise Http404
  def patch(self, request, pk, format=None):
    company = self.get_object(pk)
    if request.data['location']:
      location_serializer = CompanyStoreSerializer()
      serializer= ForProfitCompanySerializer(company, data = request.data, partial=True)
    if serializer.is_valid():
      serializer.save()
      return HttpResponse(status=200)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FindUserList(APIView):
  authentication_classes = (TokenAuthentication, )

  def get(self,request, format=None):

    # me = UserProfile.objects.get(user = request.user)
    users = UserProfile.objects.exclude()

    userlist = []
    for profile in users:
     serialized = ProfileRepSerializer(profile).data
     userlist.append(serialized)

    return Response(userlist)

class FollowingList(APIView):
  authentication_classes =(TokenAuthentication,)
  def get(self, request, format =None):
    following_list = []

    me = UserProfile.objects.get(user = request.user)
    for profile in me.following.all():
      representation = {'username': str(profile.username),
      'id':(profile.user.id)}
      following_list.append(representation)

    return Response(following_list)


class LinkList(viewsets.ModelViewSet):
  permission_classes= []
  serializer_class = LinkSerializer
  queryset = Link.objects.all()


class MatchRelationships(viewsets.ModelViewSet):
  permission_classes=[]
  serializer_class = CompanyNonProfitRelationshipSerializer
  queryset = CompanyNonProfitRelationship.objects.all()


def all_profile_fields_neccessary_for_stripe_object(data):
    required_fields = ['name','email']
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Field '{field}' is required for creating a Stripe customer.")
    return True

class UserProfileDetail(APIView):
    authentication_classes = [TokenAuthentication]

    def get_object(self, altid):
        try:
            return UserProfile.objects.get(user__id=altid)
        except UserProfile.DoesNotExist:
            raise Http404

    def patch(self, request, altid):
        userprofile = self.get_object(altid)
        
        # Use request.data directly, which allows for any combination of fields
        serializer = UserProfileSerializer(userprofile, data=request.data, partial=True)
        
        if serializer.is_valid():
            # Handle Stripe customer creation if needed
            if not userprofile.stripe_customer_id and request.data.get('payment_method_id'):
                try:
                    customer_data = {
                        'name': userprofile.user.get_full_name() or userprofile.username,
                        'email': userprofile.user.email,
                        
                    }
                    customer = stripe.Customer.create(**customer_data)
                    userprofile.stripe_customer_id = customer.id
                except stripe.error.StripeError as e:
                    return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class UserFriendsDonationList(APIView):
#   permission_classes=(IsAuthenticated,)
#   def


class ShirtList(viewsets.ModelViewSet):


  serializer_class = ShirtSerializer
  queryset= Shirt.objects.all()

  @action(detail=True, methods=['get'])
  def getShirt(self, request, *args, **kwargs):
    name = request.Get.get('name')
    shirt = Shirt.objects.get(name = name)
    serialized = ShirtSerializer(shirt, fields =['id','name','price','shirt_image' ])
    return serialized.data


  @action(detail=True, methods=['get'])
  def getVariation(self, request, pk):
    color = request.GET.get('color')
    variation= ShirtVariations.objects.get(shirt_id =pk , color__color = color)
    serialized = ShirtVariationSerializer(variation)
    return Response(serialized.data, status=status.HTTP_200_OK)

  @action(detail=True, methods=['POST'])
  def rate_shirt(self,request, pk=None):
    if 'stars' in request.data:
      shirt = Shirt.objects.get(id=pk)
      stars = request.data['stars']
      user = request.user



      try:
        rating = Rating.objects.get(user = user.id, shirt = shirt.id)
        rating.stars = stars
        rating.save()
        serializer = RatingSerializer(rating, many =False)
        response = {'message': 'Rating Updated', 'result':serializer.data}
        return Response(response, status=status.HTTP_200_OK)
      except:
        rating = Rating.objects.create(user =user, shirt= shirt, stars= stars)
        serializer =RatingSerializer(rating)
        response = {'message': 'Rating Created', 'result':serializer.data}
        return Response(response, status=status.HTTP_200_OK)
    else:
      response = {'messeage': 'You need to provide a rating'}
      return Response(response, status=status.HTTP_400_BAD_REQUEST)


class NpProjectList(viewsets.ModelViewSet):
  permission_classes=[]
  serializer_class= ProjectRepSerializer
  queryset = NonProfitProject.objects.all()
  @action(detail=False, methods=['get'])
  def category(self, request, *args, **kwargs):

    category = request.GET.get('cat', None)
    queryset = self.get_queryset().filter(category = category).order_by('-id')

    serializer = NonProfitProjectSerializer(queryset, many=True)
    return Response(data = serializer.data, )


class CompanyList(viewsets.ModelViewSet):
  permission_classes=[]

  serializer_class = ForProfitCompanySerializer
  queryset = ForProfitCompany.objects.all()

  # def create(self, request):
  #   profile = UserProfile.objects.get(user = request.user)
  #   serializer = ForProfitCompanySerializer(data = request.data)
  #   if serializer.is_valid:
  #     serializer.save


  @action(detail=True, methods=['patch'])
  def add_contributor(self, request, *args, **kwargs):
    company = self.get_object()
    pend_contr = company.pending_contributors.all()
    try:
      profile_instance = UserProfile.objects.get(user_id = request.data['user'])
      if profile_instance not in pend_contr:
        pend_contr.add(profile_instance)
        company.save()
        response = {"message": "You have invited {profile.username} to be a contributor"}
        return Response(response, status= status.HTTP_200_OK)
      elif profile_instance in pend_contr:
        response ={'message': 'You have already invited this user. Please wait for them to respond to your request'}
        return Response(response, status = status.HTTP_200_OK)
    except:
      response={"message":"Oops! Something went wrong, please try again"}
      return Response(response, status= status.HTTP_400_BAD_REQUEST )


  @action(detail=True, methods=['patch'])
  def deletePendingContributor(self, request, *args, **kwargs):
    company= self.get_object()
    contributors = company.contributors.all()
    pending = company.pending_contributors.all()

  @action(detail=False, methods=['get'])
  def atrocity(self, request):
    companies = ForProfitCompany.objects.filter(categories__in=[1])
    serializer = ForProfitCompanySerializer(companies, many = True)
    response = {'message': 'Companies', 'result':serializer.data}
    return Response(serializer.data)


class RegisterCompany(generics.CreateAPIView):
  authentication_classes=(TokenAuthentication,)
  serializer_class = ForProfitCompanySerializer

  def post(self, request):
    profile = get_object_or_404(UserProfile, user = request.user )
    if profile.pk == request.data['owner']['user']:
      serialized= ForProfitCompany.objects.create(mission =request.data['mission'], name = request.data['name'], owner = profile, year_started = request.data['year_started'], description= request.data['description'],website_address = request.data['website_address'] )
      if serialized:
        profile.has_company = True
        profile.save(update_fields =['has_company'])
        serial = ForProfitCompanySerializer(serialized)
        response ={'message':'Company {} created'.format(serial.name), "result": serial.data}
        return Response(response,status = status.HTTP_201_CREATED)




class CreateOrderView(APIView):

    authentication_classes= (TokenAuthentication, )
    def post(self, request, *args, **kwargs):
        data = request.data.get('items')
        user = request.user  # Assuming you have authentication set up

        profile= UserProfile.objects.get(user= user)

        if not data:
            return Response({'message': 'No items provided'}, status=status.HTTP_400_BAD_REQUEST)

        order_items = []
        for item_data in data:
            ordered_shirt_id = item_data.get('shirtId')
            quantity = item_data.get('quantity')
            color = item_data.get('color')
            size_id = item_data.get('size_id')
            # Other fields...

            try:
                ordered_shirt = Shirt.objects.get(id=ordered_shirt_id)
            except Shirt.DoesNotExist:
                return Response({'message': f'Shirt with ID {ordered_shirt_id} does not exist'}, status=status.HTTP_400_BAD_REQUEST)

            try:
              shirt_color = ShirtColor.objects.get(color =color)
            except ShirtColor.DoesNotExist:
              return Response({'message':f'The color {shirt_color} does not exist'})

            try:
              shirt_size = ShirtSize.objects.get(id= size_id)
            except ShirtSize.DoesNotExist:
              return Response({'message':f'The color {shirt_size} does not exist'})

            order_item = OrderItem.objects.create(
                user=profile,
                ordered_shirt=ordered_shirt,
                quantity=quantity,
                color=shirt_color,
                size=shirt_size,
                ordered=False
            )

            order_items.append(order_item)

        order = Order.objects.create(user=profile)
        order.shirts.set(order_items)
        order.save()
        response = {'message':'Your order has been placed', "result": 'serial.data'}
        return Response(response, status=status.HTTP_201_CREATED)


class NpProjectView(APIView):
    parser_classes = (JSONParser, MultiPartParser)
    serializer_class = NonProfitProjectSerializer

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        data = request.data

        # Get the related objects
        nonprofit = NonProfit.objects.get(id=data.get('nonprofit'))
        atrocity = Atrocity.objects.get(id=data.get('atrocity')) if data.get('atrocity') else None
        category = Category.objects.get(id=data.get('category')) if data.get('category') else None

        # Create the project
        project = NonProfitProject(
            nonprofit=nonprofit,
            atrocity=atrocity,
            category=category,
            title=data.get('title'),
            fundraising_goal=data.get('fundraisingGoal'),
            information=data.get('information'),
            supplies=data.get('supplies'),
            project_image=request.FILES.get('project_image'),
            project_image_url=data.get('project_image_url')
        )

        project.save()

        # Serialize and return the response
        serialized = NonProfitProjectSerializer(project)
        response = {
            'message': f'NonProfitProject {project.title} created',
            'result': serialized.data
        }
        return Response(response, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        data = request.data
        project_id = kwargs.get('pk')

        try:
            project = NonProfitProject.objects.get(id=project_id)
        except NonProfitProject.DoesNotExist:
            return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

        # Update the related objects if provided
        if 'nonprofit' in data:
            nonprofit = NonProfit.objects.get(id=data.get('nonprofit'))
            project.nonprofit = nonprofit

        if 'atrocity' in data:
            atrocity = Atrocity.objects.get(id=data.get('atrocity')) if data.get('atrocity') else None
            project.atrocity = atrocity

        if 'category' in data:
            category = Category.objects.get(id=data.get('category')) if data.get('category') else None
            project.category = category

        # Update other fields
        project.title = data.get('title', project.title)
        project.fundraising_goal = data.get('fundraisingGoal', project.fundraising_goal)
        project.information = data.get('information', project.information)
        project.supplies = data.get('supplies', project.supplies)
        project.project_image = request.FILES.get('project_image', project.project_image)
        project.project_image_url = data.get('project_image_url', project.project_image_url)

        project.save()

        # Serialize and return the response
        serialized = NonProfitProjectSerializer(project)
        response = {
            'message': f'NonProfitProject {project.title} updated',
            'result': serialized.data
        }
        return Response(response, status=status.HTTP_200_OK)


class ShirtVariation(APIView):
  def get(self, shirt_id, **kwargs):

    color = self.request.GET.get('color')
    variation = ShirtVariation.object.get(shirt_id = shirt_id, color_color = color)
    serialized = ShirtVariationSerializer(variation)
    return serialized.data


class ShirtVariationsList(viewsets.ModelViewSet):
  permission_classes = []
  serializer_class = ShirtVariationSerializer
  queryset = ShirtVariations.objects.all()

  @action(detail=True, methods='get', )
  def shirt(self, request, *args, **kwargs):
    shirt = request.GET.get('shirt', None)
    color = request.GET.get('color', None)
    queryset = self.get_queryset().filter(shirt = shirt, color__color = color)
    serializer = ShirtVariationSerializer(queryset)
    return serializer.data


class RegisterNonProfit(generics.CreateAPIView):
  authentication_classes =(TokenAuthentication,)
  serializer_class = NonProfitSerializer
  def post(self, request):
    profile = get_object_or_404(UserProfile, user = request.user)
    if profile.pk == request.data['owner']['user']:
      serialized = NonProfit.objects.create(mission_statement = request.data['mission_statement'], name =request.data['name'], vision_statement =request.data['vision_statement'], year_started = request.data['year_started'], description = request.data['description'], website_url= request.data['website_url'], instagram = request.data['instagram'], facebook = request.data['facebook'], owner = profile )
    if serialized:
      profile.has_nonprofit = True
      profile.save(update_fields=['has_nonprofit'])
      serial = NonProfitSerializer(serialized)
      response ={'message':'NonProfit ${} created'.format(serialized.name), "result": serial.data}
      return Response(response, status= status.HTTP_201_CREATED)
    return Response(serialized.errors)


class RatingViewSet(viewsets.ModelViewSet):
  queryset = Rating.objects.all()
  serializer_class = RatingSerializer
  authentication_classes = (TokenAuthentication, )


class RateItem(generics.CreateAPIView):
  authentication_classes = (TokenAuthentication,)
  serializer_class= RatingSerializer
  def post(self, request):
    profile = get_object_or_404(UserProfile, user = request.user.id)

    print(profile)
    if request.data['shirt'] is not None:
      shirt = Shirt.objects.get(pk = request.data['shirt'])
      serialized = Rating.objects.create(shirt = shirt,

                                    stars =request.data['stars'],
                                    user =profile)
    if request.data['project'] is not None:
      project = NonProfitProject.objects.get(pk= request.data['project'])
      serialized = Rating.objects.create(project = project,stars =request.data['stars'],
       user =profile)
    if request.data['nonprofit'] is not None:
      nonprofit = NonProfit.objects.get(pk= request.data['nonprofit'])
      serialized = Rating.objects.create(nonprofit = nonprofit,
       stars =request.data['stars'],user =profile)
    if request.data['company'] is not None:
      company = ForProfitCompany.objects.get(pk=request.data['company'])
      serialized = Rating.objects.create(company = company,

                                    stars =request.data['stars'],
                                    user =profile)
    if serialized:
      response = {'message':'You have just rated', 'result':'rated'}
      return Response(response, status= status.HTTP_201_CREATED)
    return Response(serialized.errors)


class CompanyMatchNonProfit(generics.CreateAPIView):
  authentication_classes= (TokenAuthentication, )
  serializer_class = CompanyNonProfitRelationshipSerializer

  def post(self, request):
    profile = get_object_or_404(UserProfile, user = request.user.id)
    funding_limit = request.data['funding_limit']
    match_level = request.data['match_level']
    company= ForProfitCompany.objects.get(owner = profile)
    print(company)
    if request.data['nonprofit'] is not None:
      nonprofit = NonProfit.objects.get(pk= request.data['nonprofit']['id'])

    serialized = CompanyNonProfitRelationship.objects.create(company = company, match_level = match_level, funding_limit=funding_limit, nonprofit = nonprofit)
    if serialized:
      serial= CompanyNonProfitRelationshipSerializer(serialized)
      response = {'message':'You have created a new matching relationship','result':serial.data}
      return Response(response, status = status.HTTP_201_CREATED)
    print(serialized.errors)
    return Response(serialized.errors)


class NonProfitList(viewsets.ModelViewSet):
  permission_classes = []
  serializer_class = NonProfitSerializer
  queryset= NonProfit.objects.all()

  @action(detail=False, methods=['get'])
  def category(self, request, *args, **kwargs):

    category = request.GET.get('cat', None)
    queryset = self.get_queryset().filter(category = category).order_by('-id')

    serializer = NonProfitSerializer(queryset, many=True)
    return Response(data = serializer.data, )


class AtrocityList(viewsets.ModelViewSet):
  permission_classes = []
  serializer_class = AtrocitySerializer
  queryset= Atrocity.objects.all().order_by('-id')

  @action(detail = False, methods=['get'])
  def category(self, request, *args, **kwargs):
    cat = request.GET.get('cat', None)
    queryset = self.get_queryset().filter(category = cat)
    serializer = AtrocitySerializer(queryset, many = True)
    return Response(data= serializer.data)


class ShirtGroupList(viewsets.ModelViewSet):
   permission_classes=[]
   serializer_class = ShirtGroupSerializer
   queryset = ShirtGroup.objects.all()


class QuizList(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = []

    @action(detail=False, methods=['GET'])
    def filter_by_category(self, request):
        category_id = request.query_params.get('category_pk')
        if category_id is not None:
            quizzes = Quiz.objects.filter(category_id=category_id)
            serializer = QuizSerializer(quizzes, many=True)
            return Response(serializer.data)
        else:
            return Response({'error': 'Category ID is required'}, status=400)


class CategoryList(viewsets.ModelViewSet):
  permission_classes = []
  serializer_class = CategorySerializer
  queryset= Category.objects.all()


class NonProfitByCategory(generics.ListAPIView):
  permission_class = []
  serializer_class = NonProfitSerializer

  def get_queryset(self):
      return NonProfit.objects.filter(category= self.kwargs['pk']).order_by('-id')


class PovertyShirts(generics.ListAPIView):
  permission_classes =[]
  serializer_class = ShirtSerializer

  def get_queryset(self):
    return Shirt.objects.filter(category_id= 3).order_by('-id')


class RefugeeShirts(generics.ListAPIView):
  permission_classes=[]
  serializer_class = ShirtSerializer
  def get_queryset(self):
      return Shirt.objects.filter(category_id = 2).order_by('-id')


class WorldHungerShirts(generics.ListAPIView):
  permission_classes = []
  serializer_class = ShirtSerializer
  def get_queryset(self):
    return Shirt.objects.filter(category_id =1).order_by('-id')


class AltrueLevelsList(viewsets.ModelViewSet):
    permission_classes = []
    serializer_class = AltrueLevelSerializer
    queryset= AltrueLevel.objects.all()


class FeaturedShirts(generics.ListAPIView):
  permission_classes = []
  serializer_class = ShirtSerializer

  def get_queryset(self):
    return Shirt.objects.filter(featured = True).order_by('-id')


class FeaturedAtrocities(generics.ListAPIView):
  permission_classes = []
  serializer_class = AtrocitySerializer

  def get_queryset(self):
    return Atrocity.objects.filter(featured = True).order_by('-id')


class FeaturedNonProfitProjects(generics.ListAPIView):
  permission_classes = []
  serializer_class = ProjectRepSerializer

  def get_queryset(self):
    return NonProfitProject.objects.filter(featured = True).order_by('-id')


class AllUserDonations(viewsets.ModelViewSet):
  queryset = UserDonation.objects.all().order_by('donation_date')
  serializer_class =UserDonationSerializer


class FeaturedNonProfits(generics.ListAPIView):
  permission_classes = []
  serializer_class = NonProfitSerializer

  def get_queryset(self):
    return NonProfit.objects.filter(featured = True).order_by('-id')


class UserOrder(viewsets.ModelViewSet):
  permission_classes = (IsAuthenticated, )
  serializer_class= OrderSerializer
  queryset = Order.objects.all()

  @action(detail=True, methods = ["GET"])
  def get_cart(self, request, *args, **kwargs):
    user = request.user
    profile = UserProfile.objects.get(user = user)
    cart = Order.objects.filter(completed = False, user = profile).order_by('-id')

    return cart


class QuizResultReceiveView(APIView):
    def post(self, request, format=None):
        serializer = QuizResultSerializer(data=request.data)
        if serializer.is_valid():
            actions = []
            serializer.save()
            quiz_id = serializer.validated_data['quiz']
            profile_id = serializer.validated_data['user']
            score = serializer.validated_data['score']
            try:
                if score>=70:
                    profile = UserProfile.objects.get(id = profile_id)
                    quiz = Quiz.objects.get(id=quiz_id)
                    if quiz.atrocity:
                        the_actions = record_user_action(profile,'passquiz',{'quiz_id':quiz.id})
                        serialized_actions = UserActionSerializer(the_actions, many=True)
                        actions.append(serialized_actions)
                        
                    if quiz.category:
                        the_actions = record_user_action(profile, 'passCauseQuiz', {"quiz_id":quiz.id})
                        serialized_actions = UserActionSerializer(the_actions, many=True)
                        actions.append(serialized_actions, many=True)
                
                    response = {}
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                
            except(UserProfile.DoesNotExist, Quiz.DoesNotExist):
                return Response({'detail': 'User or quiz not found'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 

class UserCompletedOrders(viewsets.ModelViewSet):
  authentication_classes = []
  serializer_class= OrderSerializer

  # user = request.user
  # profile = UserProfile.objects.get(user = user)

  # open_order = Order.objects.filter(completed=False, user= profile )

class FeedView(APIView):
    # authentication_classes =[TokenAuthentication,]
    def get(self, request, *args, **kwargs):
       now = timezone.now()

       today_start = now.replace(hour =0, minute=0, second=0, microsecond=0)

       point_transactions = PointTransaction.objects.filter(timestamp__gte = today_start)
       donations = Donation.objects.filter(donation_date__gte=today_start)

       point_transactions_data = PointTransactionSerializer(point_transactions, many=True).data
       donations_data = DonationSerializer(donations,many=True).data

       feed_data =sorted(point_transactions_data + donations_data,
                         key=lambda x: x['timestamp'] if 'timestamp' in x else x['donation_date'],
                         reverse=True)
       
       return Response(feed_data)
       
       


class LeaderBoardView(APIView):
    def get(self, request, format=None):
        profiles = UserProfile.objects.all().annotate(
            total_balance=F('altrue_points__balance')
        ).order_by('-total_balance', 'user__username')  # Order by points first, then by username to keep consistency

        serialized_profiles = LeaderBoardSerializer(profiles, many=True).data

        # Add ranking with tie handling
        rank = 1
        last_balance = None
        rank_count = 0

        for profile in serialized_profiles:
            if profile['total_balance'] != last_balance:
                rank = rank + rank_count
                rank_count = 1
            else:
                rank_count += 1

            profile['rank'] = rank
            last_balance = profile['total_balance']

        return Response(serialized_profiles)


class AllUserCompletedOrders(generics.ListAPIView):
  authentication_classes = [TokenAuthentication, ]
  serializer_class = OrderSerializer

  def get_queryset(self):
    user = self.request.user.profile
    return Order.objects.filter(user = user).order_by('-id')


class UserFollowerDonations(APIView):
  permission_classes = [IsAuthenticated]
  serializer_class = UserProfileSerializer


  def get(self, request, format=None):
        profile = request.user
        friend_list =[]
        new_list =[]
        nonprofit = NonProfit.objects.get(id = request.data['id'])
        userprofile = UserProfile.objects.filter(user = profile)
        followers = userprofile.following.all()
        for follower in followers:
          donations = UserDonation.objects.filter(user = follower).order_by('-id')

          for donation in donations:
            if donation.nonprofit is nonprofit:
              friend_list.append(follower)
          for friend in friend_list:
            serializer = UserProfileSerializer(friend_list, many =True)
        return Response(serializer.data)


class ShirtGroupsList(APIView):
  permission_classes =[]
  serializer_class = ShirtSerializer



  def get(self, request, format=None):
    shirtList=[]
    shirts= Shirt.objects.filter(shirt_group)
    for shirt in shirts:
      shirtList.append(shirt)

    serializer = ShirtSerializer(shirtList, many =True)
    return Response(serializer.data)


class ProcessPaymentAPIView(APIView):
    authentication_classes =[TokenAuthentication, ]
    def post(self, request):
        # Retrieve payment token from the request
        token = request.data.get("token")

        try:
            # Create a charge using the payment token
            charge = stripe.Charge.create(
                amount=1000,  # Amount in cents (e.g., $10.00)
                currency="usd",
                source=token,
                description="Example Charge"
            )

            # Payment was successful, create objects in your database
            # For example, create an Order object
            order = Order.objects.create(
                user=request.user,
                amount=charge.amount,
                # Add more fields as needed
            )

            # Return success response to frontend
            return Response({"success": True, "message": "Payment processed successfully", "order_id": order.id}, status=status.HTTP_200_OK)

        except stripe.error.CardError as e:
            # Card was declined or other error occurred
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_share_record(request):
    """
    Creates a new ShareRecord object based on the provided data.

    Requires authentication and expects the following POST parameters:
    - `atrocity_id` (optional): ID of the Atrocity to associate with the ShareRecord.
    - `nonprofit_id` (optional): ID of the NonProfit to associate with the ShareRecord.
    - `nonprofit_project_id` (optional): ID of the NonProfitProject to associate with the ShareRecord.

    Returns a JSON response with the created ShareRecord object and user actions (if applicable).
    """

    userprofile = request.user.userprofile  # Assuming UserProfile is related to the user model

    # Validate data based on the provided IDs
    if 'atrocity_id' in request.data:
        try:
            atrocity = Atrocity.objects.get(id=request.data.get('atrocity_id'))
            share_record = ShareRecord.objects.create(user=userprofile, atrocity=atrocity)
            action_type = 'shareAtrocity'
        except Atrocity.DoesNotExist:
            return JsonResponse({'error': 'Atrocity not found'}, status=404)
    elif 'nonprofit_id' in request.data:
        try:
            nonprofit = NonProfit.objects.get(id=request.data.get('nonprofit_id'))
            share_record = ShareRecord.objects.create(user=userprofile, nonprofit=nonprofit)
            action_type = 'shareNonProfit'
        except NonProfit.DoesNotExist:
            return JsonResponse({'error': 'NonProfit not found'}, status=404)
    elif 'nonprofit_project_id' in request.data:
        try:
            project = NonProfitProject.objects.get(id=request.data.get('nonprofit_project_id'))
            share_record = ShareRecord.objects.create(user=userprofile, project=project)
            action_type = 'shareProject'
        except NonProfitProject.DoesNotExist:
            return JsonResponse({'error': 'NonProfitProject not found'}, status=404)
    elif 'quiz_id' in request.data:
        try:
          quiz = Quiz.objects.get(id= request.data.get('quiz_id'))
          share_record = ShareRecord.objects.create(user=userprofile, quiz=quiz)
          action_type = 'shareQuiz'
        except Quiz.DoesNotExist:
           return JsonResponse({'error': 'Quiz was not found'}, statis =404)
    else:
        return JsonResponse({'error': 'Missing required field: atrocity_id, nonprofit_id, or nonprofit_project_id'}, status=400)

    # Handle successful share record creation
    if share_record:
        actions = record_user_action(userprofile, action_type, {'shareRecord': share_record})
        serialized_actions = UserActionSerializer(actions, many=True).data
        response_data = {"success": "Share Recorded", "actions": serialized_actions}
        return JsonResponse(response_data, status=status.HTTP_201_CREATED)
    else:
        return JsonResponse({'error': 'Failed to create ShareRecord'}, status=400)
               
class CreateHybridPayment(APIView):
   authentication_classes =(TokenAuthentication,)

   def post(self, request, *args, **kwargs):
      data = json.loads(request.body)
      user_id = data.get("user_id")
      if request.user.is_authenticated:
          try:
            userprofile = UserProfile.objects.get(pk=user_id)
          except UserProfile.DoesNotExist:
            return JsonResponse(
                {"error": "User does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
      else:
        return JsonResponse(
            {"error": "User is not authenticated"},
            status=status.HTTP_401_UNAUTHORIZED,
          )
      shirts = data.get('shirt')
      order_id = data.get("order_id")
      partial_point_payment = data.get("point_payment")


      purchase_total_amount=0

      for the_shirt in shirts:
          item_amount= the_shirt['quantity'] * the_shirt['points_needed_to_purchase']
          purchase_total_amount+=item_amount


      remaining_points = purchase_total_amount - partial_point_payment

      print({'the point total for the whole purchase':[purchase_total_amount]})
      print({'the amount beeing spent':partial_point_payment})
      order=Order.objects.get(id=order_id)
      userWallet = AltruePoints.objects.get(account=userprofile)
      print({"old_balance":userWallet.balance})
      print(purchase_total_amount)
      if userWallet.balance>= partial_point_payment:
          userWallet.balance-=partial_point_payment
          userWallet.save()
          order.payment_type = 3
          order.points_paid = partial_point_payment
          order.save()

      userprofile.altrue_level

      #need to convert the remainiing point balance to dollars for the
      conversion_rate= PointSystemConversionRate.objects.get(is_active=True).rate_value
      print(f'the math is {remaining_points} divided by {conversion_rate}')
      remaining_amount_in_dollars =  float(remaining_points / conversion_rate)
      print({"The amount left is":remaining_amount_in_dollars})
      try:
          stripe.PaymentIntent.cancel(order.stripe_id)
          new_intent = stripe.PaymentIntent.create(
            amount = int(remaining_amount_in_dollars*100),
            currency ='usd',
          )

          order.stripe_id = new_intent.id
          order.save()
          response_data = {
                  "order_id": order.id,
                  "clientSecret": new_intent,
                  "amount_remaining":remaining_amount_in_dollars
                }
          return JsonResponse(response_data, status=status.HTTP_201_CREATED)
      except stripe.error.StripeError as e:
            # Handle any Stripe errors
          return JsonResponse({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CreatePurchaseWithPoints(APIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request, *args, **kwargs):
        print(request.user)
        data = json.loads(request.body)
        user_id = data.get("user_id")
        if request.user.is_authenticated:
            try:
                userprofile = UserProfile.objects.get(pk=user_id)
            except UserProfile.DoesNotExist:
                return JsonResponse(
                    {"error": "User does not exist"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            return JsonResponse(
                {"error": "User is not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        SIZE_MAPPING = {"XS": 1, "S": 2, "M": 3, "L": 4, "XL": 5, "XXL": 6}

        shirts = data.get("shirt")
        order_id= data.get("order_id")
        print(shirts)
        print(order_id)

        purchase_total_amount=0

        for the_shirt in shirts:
            item_amount= the_shirt['quantity'] * the_shirt['points_needed_to_purchase']
            purchase_total_amount+=item_amount




        order=Order.objects.get(id=order_id)



        userWallet = AltruePoints.objects.get(account=userprofile)
        print({"old_balance":userWallet.balance})
        print(purchase_total_amount)
        if userWallet.balance >= purchase_total_amount:
          userWallet.balance -= purchase_total_amount
          userWallet.save()
          print({"new_balance":userWallet.balance})
          order.payment_type= 2
          order.stripe_id='pointPurchase'
          order.paid_for=True
          order.points_paid = purchase_total_amount
          order.amount_paid = 0
          order.save()


          return JsonResponse({"success":f'Order created using Altrue Point. New Altrue Point Balance is {userWallet.balance} '},status = status.HTTP_200_OK)
        else:
          return JsonResponse({"error": "Insufficient points to make this purchase"}, status=status.HTTP_400_BAD_REQUEST)
        #

@method_decorator(csrf_exempt, name="dispatch")
class AltrueWalletDonation(APIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request, *args, **kwargs):
        print(request.body)
        data = json.loads(request.body)
        print
        user_id = data.get("user_id")
        # if request.user.is_authenticated:
        try:
            userprofile = UserProfile.objects.get(pk=user_id)
        except UserProfile.DoesNotExist:
            return JsonResponse(
            {"error": "User does not exist"}, status=status.HTTP_404_NOT_FOUND
        )
        # else:
        #     return JsonResponse(
        #     {"error": "User is not authenticated"},
        #     status=status.HTTP_401_UNAUTHORIZED,
        #   )

        donation_amount = data.get('amount')
        nonprofit = data.get('nonprofit')
        atrocity = data.get('atrocity')
        project = data.get('project')

        userWallet = Balance.objects.get(account =userprofile)
        donation_amount = round(donation_amount, 2)

        if nonprofit is not None:
            thenonprofit = NonProfit.objects.get(id = data.get('nonprofit'))

            if donation_amount<= userWallet.balance:

                donation = UserDonation.objects.create(
                dollar_amount= donation_amount, user=userprofile, wallet=userWallet, 
                nonprofit= thenonprofit,donation_type='S',
                )
                
                actions = record_user_action(userprofile, 'makeADonation',{'nonprofit':thenonprofit.id})
                serialized_actions = UserActionSerializer(actions, many =True).data
                # donation.save()
                response_data = {"success": "Payment made and successful", "actions": serialized_actions}
                return JsonResponse(response_data, status=status.HTTP_201_CREATED)
            else:
                return JsonResponse({"error":"Insufficient funds in wallet"}, status =status.HTTP_400_BAD_REQUEST)

        elif atrocity is not None:
            theatrocity = Atrocity.objects.get(id= data.get('atrocity'))
            if donation_amount < userWallet.balance:

                donation = UserDonation.objects.create(dollar_amount= donation_amount, wallet=userWallet, atrocity=theatrocity, user=userprofile, donation_type='S')
                donation.save()
                actions = record_user_action(userprofile, 'makeADonation',{'atrocity':theatrocity.id})
                serialized_actions = UserActionSerializer(actions, many =True).data
                response_data = {"success": "Payment made and successful", "actions": serialized_actions}
                return JsonResponse(response_data, status=status.HTTP_201_CREATED)
            else:
                return JsonResponse({"error":"Insufficient funds in wallet"}, status =status.HTTP_400_BAD_REQUEST)

        elif project is not None:
            try:
                the_project = NonProfitProject.objects.get(id= data.get('project'))
                thenonprofit = NonProfit.objects.get(id = the_project.nonprofit.pk)

                if donation_amount <= userWallet.balance:
                    donation = UserDonation.objects.create(dollar_amount=donation_amount, user=userprofile, wallet=userWallet,project=the_project,nonprofit =thenonprofit,donation_type='S' )
                    # donation.save()
                    actions = record_user_action(userprofile, 'makeADonation', {'project':the_project.id})
                    serialized_actions = UserActionSerializer(actions, many =True).data
                    response_data = {"success": "Payment made and successful", "actions": serialized_actions}
                    return JsonResponse(response_data, status=status.HTTP_201_CREATED)

                else:
                    return JsonResponse({"error":"Insufficient funds in wallet"}, status =status.HTTP_400_BAD_REQUEST)
            except NonProfitProject.DoesNotExist:
               return JsonResponse({"error":"Project not found"}, status =status.HTTP_404_NOT_FOUND)
            except NonProfit.DoesNotExist:
               return JsonResponse({"error":'NonProfit not found'})
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                return JsonResponse({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            


@method_decorator(csrf_exempt, name="dispatch")
class WalletDonation(APIView):
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            user_id = data.get("user_id")
            donation_amount = data.get('amount')
            nonprofit_id = data.get('nonprofit')
            atrocity_id = data.get('atrocity')
            project_id = data.get('project')
            code_for_action_process=''

            if not donation_amount or not isinstance(donation_amount, (int, float)):
                return JsonResponse({"error": "Invalid donation amount"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                userprofile = UserProfile.objects.get(pk=user_id)
            except UserProfile.DoesNotExist:
                return JsonResponse({"error": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)

            userWallet = Balance.objects.get(account=userprofile)
            if userWallet.balance < donation_amount:
                return JsonResponse({"error": "Insufficient funds in wallet"}, status=status.HTTP_400_BAD_REQUEST)

            donation = None
            if nonprofit_id:
                try:
                    nonprofit = NonProfit.objects.get(id=nonprofit_id)
                    donation = UserDonation.objects.create(
                        dollar_amount=donation_amount, user=userprofile, wallet=userWallet, nonprofit=nonprofit, donation_type='S')
                    actions = record_user_action(userprofile,'')
                except NonProfit.DoesNotExist:
                    return JsonResponse({"error": "Nonprofit does not exist"}, status=status.HTTP_404_NOT_FOUND)
            elif atrocity_id:
                try:
                    atrocity = Atrocity.objects.get(id=atrocity_id)
                    donation = UserDonation.objects.create(
                        dollar_amount=donation_amount, user=userprofile, wallet=userWallet, atrocity=atrocity, donation_type='S')
                    actions = record_user_action()
                except Atrocity.DoesNotExist:
                    return JsonResponse({"error": "Atrocity does not exist"}, status=status.HTTP_404_NOT_FOUND)
            elif project_id:
                try:
                    project = NonProfitProject.objects.get(id=project_id)
                    donation = UserDonation.objects.create(
                        dollar_amount=donation_amount, user=userprofile, wallet=userWallet, project=project, donation_type='S')
                    actions = record_user_action()
                except NonProfitProject.DoesNotExist:
                    return JsonResponse({"error": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND)
            else:
                return JsonResponse({"error": "No valid donation target provided"}, status=status.HTTP_400_BAD_REQUEST)

            if donation:
                userWallet.balance -= donation_amount
                userWallet.save()
                return JsonResponse({"success": "Payment made successfully"}, status=status.HTTP_201_CREATED)
            else:
                return JsonResponse({"error": "Failed to create donation"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name="dispatch")
class CreatePaymentIntentAPIView(APIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request, *args, **kwargs):
        print(request.user)
        stripe.api_key = settings.STRIPE_SECRET_KEY
        data = json.loads(request.body)
        user_id = data.get("user_id")
        if request.user.is_authenticated:
            try:
                userprofile = UserProfile.objects.get(pk=user_id)
            except UserProfile.DoesNotExist:
                return JsonResponse(
                    {"error": "User does not exist"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Handle the case where the user is not authenticated
            return JsonResponse(
                {"error": "User is not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        SIZE_MAPPING = {"XS": 1, "S": 2, "M": 3, "L": 4, "XL": 5, "XXL": 6}

        amount = data.get("amount")
        shirts = data.get("shirt")
        print(shirts)

        if amount is None:
            return JsonResponse(
                {"error": "Amount is missing"}, status=status.HTTP_400_BAD_REQUEST
            )
        print(data.get("amount"))

        orderedItems = []
        for the_shirt in shirts:

            try:
                shirt = Shirt.objects.get(id=the_shirt["shirtId"])
                print(shirt.name)
            except Shirt.DoesNotExist:
                print("the shirt doesnt exist")
                return JsonResponse(
                    {"error": "These products do not exist"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                size = SIZE_MAPPING.get(the_shirt["size"])
                shirt_size = ShirtSize.objects.get(size=size)
            except ShirtSize.DoesNotExist:
                print("the size doesnt work")
                return JsonResponse(
                    {"error": "Shirt Size does not exist"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:

                theColor = ShirtColor.objects.get(color=the_shirt["color"])
            except ShirtColor.DoesNotExist:
                print("the color doesnt exist")
                return JsonResponse(
                    {"error": "Shirt Color does not exist"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            item_ordered = OrderItem.objects.create(
                ordered_shirt=shirt,
                quantity=the_shirt["quantity"],
                size=shirt_size,
                color=theColor,
                user=userprofile,
            )

            orderedItems.append(item_ordered)
        print(orderedItems)

        try:
            product_descriptions = [str(item) for item in orderedItems]
            print("Product descriptions:", product_descriptions)  # Debugging statement

            print('I got this far')
            payment_intent = stripe.PaymentIntent.create(
                amount=amount, currency="usd"
            )
            try:
                order= Order.objects.create(
                    user = userprofile,
                    stripe_id= payment_intent.id,
                    status = 'Pending'
                )
                print("Order created successfully")
            except Exception as e:
                print(f"An error occurred while creating the order: {e}")
                return JsonResponse(
                    {"error": "Failed to create order"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )       

            order.shirts.add(*orderedItems)
            order.save()
            
            response_data = {
              "order_id": order.id,
              "clientSecret": payment_intent
            }

            print([order.id,payment_intent])
            # Return the Payment Intent's client secret
            return JsonResponse(response_data)

        except stripe.error.StripeError as e:
            # Handle any Stripe errors
            return JsonResponse({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


STRIPE_WEBHOOK_SECRET = "whsec_Pjr4V9yYr7PbuHWXhsp7CYAy5OkkzDMx"

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers["Stripe-Signature"]

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return JsonResponse({"error": str(e)}, status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return JsonResponse({"error": str(e)}, status=400)

    # Handle the event
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event['data']['object']
        payment_intent_id = event['data']['object']['id']
        amount_paid = event['data']['object']['amount_received'] / 100
        try:
            order=Order.objects.get(stripe_id = payment_intent_id)
            order.paid_for = True
            order.amount_paid = amount_paid
            order.save()
            record_user_action()
        except Order.DoesNotExist:
            pass

        donation_type = payment_intent['metadata'].get('donation_category')

        if donation_type == 'nonprofit':
            nonprofit_donation = UserDonation.objects.get(stripe_id = payment_intent_id)
            nonprofit_donation.paid_for=True
            nonprofit_donation.dollar_amount=amount_paid
            nonprofit_donation.save()

        elif donation_type =='atrocity':
            atrocity_donation= UserDonation.objects.get(stripe_id = payment_intent_id)
            atrocity_donation.paid_for=True
            atrocity_donation.dollar_amount=amount_paid
            atrocity_donation.save()

        elif donation_type == 'project':
            project_donation= UserDonation.objects.get(stripe_id= payment_intent_id)
            project_donation.paid_for=True
            project_donation.dollar_amount=amount_paid
            project_donation.save()

            pass

    elif event["type"] == "payment_intent.failed":
        # Payment failed, handle accordingly
        pass

    return JsonResponse({"received": True})

@api_view(['GET'])
def check_profile_complete(request, id):
    try:
        user = User.objects.get(pk=id)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    return Response({"profile_created": user.profile_created})


@api_view(['GET'])
def check_donation_status(request, stripe_id):
    try:
        donation = UserDonation.objects.get(stripe_id=stripe_id)
        return JsonResponse({'paid_for': donation.paid_for}, status=200)
    except UserDonation.DoesNotExist:
        return JsonResponse({'error': 'Donation not found'}, status=404)

@csrf_exempt
def get_order_status(request):
    if request.method == "POST":
        data = json.loads(request.body)
        stripe_id = data.get("stripe_id")
        
        if not stripe_id:
            return JsonResponse({"error": "Stripe ID required"}, status=400)
        
        try:
            order = Order.objects.get(stripe_id=stripe_id)
            
            # Construct response with more order details
            response_data = {
                "paid_for": order.paid_for,
                "status": order.status if hasattr(order, "status") else "Unknown",
                "shipped": order.shipped if hasattr(order, "shipped") else False,
                "tracking_number": order.tracking_number if hasattr(order, "tracking_number") else None,
            }
            
            return JsonResponse(response_data)
        
        except Order.DoesNotExist:
            return JsonResponse({"error": "Order Not Found"}, status=404)
    
    return JsonResponse({"error": "Only POST requests are allowed"}, status=405)

@csrf_exempt
def printful_webhook(request):
    if request.method == "POST":
        payload = json.loads(request.body)
        event_type = payload.get("type")
        order_id = payload.get("data").get("id")  # Get Printful order ID

        try:
            order = Order.objects.get(id=order_id)

            if event_type == "order.created":
                order.order_status = "processing"
            elif event_type == "package.shipped":
                order.order_status = "shipped"
            elif event_type == "package.delivered":
                order.order_status = "delivered"

            order.save()

        except Order.DoesNotExist:
            return JsonResponse({"error": "Order not found"}, status=404)

        return JsonResponse({"message": "Order status updated"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


COINBASE_API_URL = "https://api.commerce.coinbase.com"
API_KEY = "781e95fe-d156-4552-8de1-898ded7c7c91"

def create_charge(request):
    url = f"{COINBASE_API_URL}/charges"
    headers = {
        "Content-Type": "application/json",
        "X-CC-Api-Key": API_KEY
    }
    data = {
        "name": "The Human Fund",
        "description": "Money For People",
        "pricing_type": "fixed_price",
        "local_price": {
            "amount": "1.00",
            "currency": "USD"
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return JsonResponse(response.json())


def retrieve_charge(request, charge_id):
    url = f"{COINBASE_API_URL}/charges/{charge_id}"
    headers = {
        "X-CC-Api-Key": API_KEY
    }
    response = requests.get(url, headers=headers)
    return JsonResponse(response.json())


class GetSavedPaymentMethod(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        user = request.user  # Access user from request object

        try:
            profile = UserProfile.objects.get(user=user)
            payment_method_id = profile.payment_method_id

            if not payment_method_id:
                return Response({"error": "No saved card found"}, status=status.HTTP_404_NOT_FOUND)

            try:
                payment_method = stripe.PaymentMethod.retrieve(payment_method_id)

                # Return masked card details
                data = {'data':{
                    "last4": payment_method.card.last4,
                    "brand": payment_method.card.brand,
                    "exp_month": payment_method.card.exp_month,
                    "exp_year": payment_method.card.exp_year,
                    "card_holder_name": payment_method.billing_details.name
                }}
                return Response(data)
            except stripe.error.StripeError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except UserProfile.DoesNotExist:
            # Handle case where UserProfile is not found for the user
            return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)

def create_setup_intent(request):
    try:
        setup_intent = stripe.SetupIntent.create(
            payment_method_types=["card"],
            
            usage="off_session",  # This allows the card to be used for future payments
        )
        return JsonResponse({"client_secret": setup_intent})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

class AltrueStatisticsView(APIView):

    def get(self, request, *args, **kwargs):
        # Gather the statistics
        total_users = UserProfile.objects.count()
        total_amount_raised = Donation.objects.aggregate(Sum('donation_amount'))['donation_amount__sum'] or 0
        total_donated = UserDonation.objects.aggregate(Sum('dollar_amount'))['dollar_amount__sum'] or 0
        total_points_accumulated = AltruePoints.objects.aggregate(Sum('balance'))['balance__sum'] or 0
        total_nonprofits = NonProfit.objects.count()
        total_companies = ForProfitCompany.objects.count()
        total_atrocities = Atrocity.objects.count()
        total_donors = Donor.objects.values('email').distinct().count()

        # Prepare the data
        data = {
            'total_users': total_users, 
            'total_amount_raised': total_amount_raised,
            'total_donated': total_donated,
            'total_points_accumulated': total_points_accumulated,
            'total_nonprofits': total_nonprofits,
            'total_companies': total_companies,
            'total_atrocities': total_atrocities,
            'total_donors': total_donors,
        }

        # Serialize the data
        serializer = AltrueStatisticsSerializer(data)
        
        return Response(serializer.data)
    

class PromotedActionsView(APIView):
   
   def get(self, request):
      promoted_actions = AltrueAction.objects.filter(is_promoted=True)
      serializer = AltrueActionSerializer(promoted_actions, many =True)
      return Response(serializer.data, status= status.HTTP_200_OK)