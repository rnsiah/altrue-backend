from django.conf.urls import include
from rest_framework import routers
from api.views import  AltrueLevelsList, AltrueStatisticsView, FeedView, LeaderBoardView, PromotedActionsView, create_share_record, QuizResultReceiveView, AllUserDonations,AtrocityList, NpProjectView, WalletDonation, CategoryList, CompanyList, MatchRelationships, NonProfitList, NpProjectList, PostViewSet, QuizList, RateItem, RatingViewSet, RegisterCompany, RegisterNonProfit, ShirtGroupList , ShirtList, ShirtVariationsList, UserProfileView, UserViewSet, LinkList, UserOrder, get_order_status, stripe_webhook
from Alt.company_views import (
    CompanyApplicationViewSet, CompanyAdminViewSet, CampaignViewSet,
    MatchingView, ApplyMatchView, RewardViewSet, CompanyRewardCodesView,
    CompanyTierViewSet, CompanyInvoiceAdminViewSet
)
from django.urls import path, re_path
from . import views




router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register('ratings', RatingViewSet)
router.register('shirts', ShirtList )
router.register('levels', AltrueLevelsList)
router.register('nonprofits', NonProfitList)
router.register('userprofile', UserProfileView)
router.register('variations', ShirtVariationsList)
router.register('atrocities', AtrocityList)
router.register('order',UserOrder)
router.register(r'shirtgroups',ShirtGroupList)
# router.register('completedorders', UserCompletedOrders)
router.register('categories', CategoryList)
router.register('companies', CompanyList)
router.register('userdonations',AllUserDonations)
router.register('infolinks',LinkList)
router.register('projects',NpProjectList)
router.register('posts', PostViewSet)
router.register('quizes', QuizList)
router.register('relationships', MatchRelationships)
router.register(r'quizes/filter_by_category', QuizList, basename='quiz-filter')

# Company Ecosystem Routes
router.register('company-applications', CompanyApplicationViewSet, basename='company-application')
router.register('campaigns', CampaignViewSet, basename='campaign')
router.register('rewards', RewardViewSet, basename='reward')
router.register('admin/company-tiers', CompanyTierViewSet, basename='company-tier')
router.register('admin/company-invoices', CompanyInvoiceAdminViewSet, basename='company-invoice')


urlpatterns = [
    re_path(r"^", include(router.urls)),
    path("npList/<int:pk>", views.NonProfitByCategory.as_view()),
    path("shirtimages/<int:shirt_id>/<str:color>/", views.ShirtVariation.as_view()),    # path('usernonprofits/<int:pk>/', views.UserNonProfitsView.as_view()),
    path('userprofiles/<int:pk>/', views.UserProfileDetail.as_view()),
    path("profilepage/<int:pk>", views.UserProfileDetail.as_view()),
    path("checkprofile/<int:id>", views.check_profile_complete, name="checkprofile"),
    path("refugeesshirts", views.RefugeeShirts.as_view()),
    path("worldpovertyshirts", views.PovertyShirts.as_view()),
    path("worldhungershirts", views.WorldHungerShirts.as_view()),
    path("featuredshirts", views.FeaturedShirts.as_view()),
    path('fetchPaymentMethod/', views.GetSavedPaymentMethod.as_view()),
    path("featuredatrocities", views.FeaturedAtrocities.as_view()),
    path("featurednonprofits", views.FeaturedNonProfits.as_view()),
    path("featuredProjects", views.FeaturedNonProfitProjects.as_view()),
    path("allusercompletedorders", views.AllUserCompletedOrders.as_view()),
    path("findusers", views.FindUserList.as_view()),
    path("followingDonations/<int:id>", views.UserFollowerDonations.as_view()),
    path("registernp/", RegisterNonProfit.as_view()),
    path("rateItem/", RateItem.as_view()),
    path("registerCompany/", RegisterCompany.as_view()),
    path("createProject/", NpProjectView.as_view()),
    path("shirtgroup/", views.ShirtGroupsList.as_view()),
    path("createOrders/", views.CreateOrderView.as_view()),
    path("createCompanyNPMatch/", views.CompanyMatchNonProfit.as_view()),
    # path('create_payment_intent/', create_payment_intent,name='create_payment_intent'),
    path("payment_process/", stripe_webhook, name="payment_process"),
    path('record_share/', create_share_record, name='create_share-record'),
    path('quiz-results/', QuizResultReceiveView.as_view(), name='quiz_results'),
    path(
        "create_payment_intent/",
        views.CreatePaymentIntentAPIView.as_view(),
        name="create_payment_intent",
    ),
    path(
        "donations/status/<str:stripe_id>/",
        views.check_donation_status,
        name="check_donation_status",
    ),
    path('leaderboard/points/', LeaderBoardView.as_view(), name='leaderboard'),

    path("hybrid_payment/", views.CreateHybridPayment.as_view(), name="hybrid_payment"),
    path(
        "point_payment/", views.CreatePurchaseWithPoints.as_view(), name="point_payment"
    ),
    path("walletdonation/", views.WalletDonation.as_view(), name="wallet_donation"),
    path(
        "donate/", views.AltrueWalletDonation.as_view()
    ),  # Replace 'donate' with your desired path name
    path("order_status/", get_order_status, name="order_status"),
    path("getsetupintent", views.create_setup_intent),
    path('feedView/', FeedView.as_view(), name ='feedview'),
    path('altruestatistics/', AltrueStatisticsView.as_view(), name='altrue_statistics'),
    path('promoted-actions/', PromotedActionsView.as_view(), name='promoted-actions'),

    # =========================================================================
    # COMPANY ECOSYSTEM API ENDPOINTS - Phase 1
    # =========================================================================
    
    # Company Admin Endpoints
    path('companies/<int:pk>/dashboard/', CompanyAdminViewSet.as_view({'get': 'dashboard'}), name='company-dashboard'),
    path('companies/<int:pk>/wallet/', CompanyAdminViewSet.as_view({'get': 'wallet'}), name='company-wallet'),
    path('companies/<int:pk>/wallet/deposit/', CompanyAdminViewSet.as_view({'post': 'deposit'}), name='company-wallet-deposit'),
    path('companies/<int:pk>/invoices/', CompanyAdminViewSet.as_view({'get': 'invoices'}), name='company-invoices'),
    path('companies/<int:pk>/campaigns/', CompanyAdminViewSet.as_view({'get': 'campaigns', 'post': 'campaigns'}), name='company-campaigns'),
    path('companies/<int:pk>/rewards/', CompanyAdminViewSet.as_view({'get': 'rewards', 'post': 'rewards'}), name='company-rewards'),
    path('companies/<int:company_id>/rewards/<int:reward_id>/codes/', CompanyRewardCodesView.as_view(), name='company-reward-codes'),
    
    # Campaign Management
    path('campaigns/<int:pk>/fund/', CampaignViewSet.as_view({'post': 'fund'}), name='campaign-fund'),
    path('campaigns/<int:pk>/launch/', CampaignViewSet.as_view({'post': 'launch'}), name='campaign-launch'),
    path('campaigns/<int:pk>/pause/', CampaignViewSet.as_view({'post': 'pause'}), name='campaign-pause'),
    path('campaigns/<int:pk>/resume/', CampaignViewSet.as_view({'post': 'resume'}), name='campaign-resume'),
    
    # Matching Endpoints
    path('matches/available/', MatchingView.as_view(), name='matches-available'),
    path('donations/<int:donation_id>/match/', ApplyMatchView.as_view(), name='donation-apply-match'),
    
    # Reward Endpoints
    path('rewards/my/', RewardViewSet.as_view({'get': 'my'}), name='rewards-my'),
    path('rewards/<int:pk>/claim/', RewardViewSet.as_view({'post': 'claim'}), name='reward-claim'),

    # path('cart', views.GetCart.as_view()),
]


