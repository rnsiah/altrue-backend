import logging
from decimal import Decimal
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
from rest_framework import viewsets, generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.exceptions import PermissionDenied

from Alt.models import (
    CompanyTier, CompanyWallet, CompanyApplication, CompanyMatchCampaign,
    CampaignEscrowTransaction, CompanyInvoice, CompanyReward, CompanyRewardCode,
    UserRewardClaim, WalletTransaction, ForProfitCompany
)
from Alt.company_serializers import (
    CompanyTierSerializer, CompanyWalletSerializer, CompanyWalletSimpleSerializer,
    WalletTransactionSerializer, CompanyApplicationSerializer, CompanyApplicationAdminSerializer,
    CompanyMatchCampaignSerializer, CompanyMatchCampaignListSerializer,
    CampaignEscrowTransactionSerializer, CompanyInvoiceSerializer,
    CompanyRewardSerializer, CompanyRewardListSerializer, CompanyRewardCodeSerializer,
    CompanyRewardCodeBulkUploadSerializer, UserRewardClaimSerializer,
    UserRewardClaimCreateSerializer, CompanyDashboardSerializer,
    AvailableMatchSerializer, MatchApplicationSerializer, CompanyMatchResultSerializer,
    CampaignFundSerializer
)
from api.models import UserProfile, UserDonation

logger = logging.getLogger(__name__)


class IsCompanyOwner(permissions.BasePermission):
    """Permission to check if user owns the company"""
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, ForProfitCompany):
            return obj.owner == request.user.profile
        # For other models with company relation
        if hasattr(obj, 'company'):
            return obj.company.owner == request.user.profile
        return False


class IsAdminUser(permissions.BasePermission):
    """Permission for admin users"""
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class CompanyApplicationViewSet(viewsets.ModelViewSet):
    """
    Public endpoints for company applications.
    POST /api/company-applications/ - Submit application
    GET /api/company-applications/{id}/ - Check status
    """
    queryset = CompanyApplication.objects.all()
    serializer_class = CompanyApplicationSerializer
    permission_classes = [AllowAny]
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy', 'list']:
            return [IsAuthenticated(), IsAdminUser()]
        return [AllowAny()]
    
    def get_serializer_class(self):
        if self.request.user and self.request.user.is_staff:
            return CompanyApplicationAdminSerializer
        return CompanyApplicationSerializer
    
    def create(self, request, *args, **kwargs):
        """Submit a new company application"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            'message': 'Application submitted successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminUser])
    def approve(self, request, pk=None):
        """Admin: Approve a company application"""
        application = self.get_object()
        application.status = 'approved'
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save()
        return Response({
            'message': 'Application approved',
            'data': CompanyApplicationAdminSerializer(application).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminUser])
    def reject(self, request, pk=None):
        """Admin: Reject a company application"""
        application = self.get_object()
        reason = request.data.get('reason', '')
        application.status = 'rejected'
        application.rejection_reason = reason
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save()
        return Response({
            'message': 'Application rejected',
            'data': CompanyApplicationAdminSerializer(application).data
        })


class CompanyAdminViewSet(viewsets.ViewSet):
    """
    Company admin endpoints.
    All require authentication and company ownership.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_company(self, pk):
        """Get company and verify ownership"""
        company = get_object_or_404(ForProfitCompany, pk=pk)
        if company.owner != self.request.user.profile:
            raise PermissionDenied("You do not own this company")
        return company
    
    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """GET /api/companies/{id}/dashboard/ - Overview stats"""
        company = self.get_company(pk)
        
        # Get or create related objects
        tier, _ = CompanyTier.objects.get_or_create(company=company, defaults={'tier': 'free'})
        wallet, _ = CompanyWallet.objects.get_or_create(company=company, defaults={'monthly_budget': 0})
        
        # Campaign stats
        campaigns = company.campaigns.all()
        total_campaigns = campaigns.count()
        active_campaigns = campaigns.filter(status='active').count()
        
        # Matching stats
        total_matched_this_month = wallet.matched_this_month
        total_matched_all_time = campaigns.aggregate(
            total=Sum('amount_matched')
        )['total'] or Decimal('0')
        unique_donors_reached = campaigns.aggregate(
            total=Sum('unique_donors')
        )['total'] or 0
        
        # Rewards stats
        rewards = company.rewards.all()
        total_rewards = rewards.count()
        active_rewards = rewards.filter(status='active').count()
        total_claims = UserRewardClaim.objects.filter(
            reward__company=company
        ).count()
        
        # Recent activity
        recent_campaigns = campaigns.order_by('-created_at')[:5]
        recent_invoices = company.invoices.order_by('-created_at')[:5]
        
        data = {
            'company': company,
            'tier': tier,
            'wallet': wallet,
            'total_campaigns': total_campaigns,
            'active_campaigns': active_campaigns,
            'total_matched_this_month': total_matched_this_month,
            'total_matched_all_time': total_matched_all_time,
            'unique_donors_reached': unique_donors_reached,
            'total_rewards': total_rewards,
            'active_rewards': active_rewards,
            'total_claims': total_claims,
            'recent_campaigns': recent_campaigns,
            'recent_invoices': recent_invoices
        }
        
        serializer = CompanyDashboardSerializer(data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def wallet(self, request, pk=None):
        """GET /api/companies/{id}/wallet/ - Balance & transactions"""
        company = self.get_company(pk)
        wallet, _ = CompanyWallet.objects.get_or_create(
            company=company,
            defaults={'monthly_budget': 0}
        )
        serializer = CompanyWalletSerializer(wallet)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deposit(self, request, pk=None):
        """POST /api/companies/{id}/wallet/deposit/ - Add funds"""
        company = self.get_company(pk)
        wallet, _ = CompanyWallet.objects.get_or_create(
            company=company,
            defaults={'monthly_budget': 0}
        )
        
        amount = request.data.get('amount')
        stripe_payment_intent_id = request.data.get('stripe_payment_intent_id')
        
        if not amount or not stripe_payment_intent_id:
            return Response({
                'error': 'amount and stripe_payment_intent_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid amount'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create transaction
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='deposit',
            amount=amount,
            stripe_payment_intent_id=stripe_payment_intent_id,
            description=f'Deposit via Stripe'
        )
        
        # Update balance
        wallet.balance += amount
        wallet.save()
        
        # Check if wallet was paused and should be unpaused
        if wallet.is_paused and wallet.balance >= wallet.auto_pause_threshold:
            wallet.is_paused = False
            wallet.pause_reason = None
            wallet.save()
        
        serializer = CompanyWalletSerializer(wallet)
        return Response({
            'message': f'Successfully deposited ${amount}',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def invoices(self, request, pk=None):
        """GET /api/companies/{id}/invoices/ - Billing history"""
        company = self.get_company(pk)
        invoices = company.invoices.all().order_by('-month')
        serializer = CompanyInvoiceSerializer(invoices, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get', 'post'])
    def campaigns(self, request, pk=None):
        """
        GET /api/companies/{id}/campaigns/ - List campaigns
        POST /api/companies/{id}/campaigns/ - Create campaign
        """
        company = self.get_company(pk)
        
        if request.method == 'GET':
            campaigns = company.campaigns.all().order_by('-created_at')
            serializer = CompanyMatchCampaignListSerializer(campaigns, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            data = request.data.copy()
            data['company_id'] = company.id
            
            serializer = CompanyMatchCampaignSerializer(data=data)
            if serializer.is_valid():
                campaign = serializer.save()
                return Response({
                    'message': 'Campaign created successfully',
                    'data': CompanyMatchCampaignSerializer(campaign).data
                }, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get', 'post'])
    def rewards(self, request, pk=None):
        """
        GET /api/companies/{id}/rewards/ - List company rewards
        POST /api/companies/{id}/rewards/ - Create reward
        """
        company = self.get_company(pk)
        
        if request.method == 'GET':
            rewards = company.rewards.all().order_by('-created_at')
            serializer = CompanyRewardSerializer(rewards, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            data = request.data.copy()
            data['company_id'] = company.id
            
            serializer = CompanyRewardSerializer(data=data)
            if serializer.is_valid():
                reward = serializer.save()
                return Response({
                    'message': 'Reward created successfully',
                    'data': CompanyRewardSerializer(reward).data
                }, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CampaignViewSet(viewsets.ModelViewSet):
    """
    Campaign endpoints.
    POST /api/campaigns/{id}/fund/ - Fund escrow (30%)
    GET /api/campaigns/{id}/
    PATCH /api/campaigns/{id}/ - Update/pause
    """
    queryset = CompanyMatchCampaign.objects.all()
    serializer_class = CompanyMatchCampaignSerializer
    authentication_classes = [TokenAuthentication]
    lookup_field = 'pk'
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy', 'fund']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Public can only see active campaigns
        if not self.request.user.is_authenticated:
            return queryset.filter(status='active')
        return queryset
    
    def get_company_from_campaign(self, campaign):
        """Get company and verify ownership"""
        company = campaign.company
        if company.owner != self.request.user.profile:
            raise PermissionDenied("You do not own this company")
        return company
    
    @action(detail=True, methods=['post'])
    def fund(self, request, pk=None):
        """POST /api/campaigns/{id}/fund/ - Fund escrow (30%)"""
        campaign = self.get_object()
        company = self.get_company_from_campaign(campaign)
        
        serializer = CampaignFundSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        amount = serializer.validated_data['amount']
        stripe_payment_intent_id = serializer.validated_data['stripe_payment_intent_id']
        
        # Validate minimum funding (30% of budget)
        if amount < campaign.required_escrow:
            return Response({
                'error': f'Minimum funding required: ${campaign.required_escrow}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create escrow transaction
        CampaignEscrowTransaction.objects.create(
            campaign=campaign,
            transaction_type='deposit',
            amount=amount,
            stripe_payment_intent_id=stripe_payment_intent_id,
            description='Campaign escrow funding'
        )
        
        # Update campaign
        campaign.escrow_funded += amount
        if campaign.is_fully_funded and campaign.status == 'pending_funding':
            campaign.status = 'draft'  # Ready to launch
        campaign.save()
        
        return Response({
            'message': f'Successfully funded ${amount}',
            'data': CompanyMatchCampaignSerializer(campaign).data
        })
    
    @action(detail=True, methods=['post'])
    def launch(self, request, pk=None):
        """Launch a funded campaign"""
        campaign = self.get_object()
        company = self.get_company_from_campaign(campaign)
        
        if not campaign.is_fully_funded:
            return Response({
                'error': 'Campaign must be fully funded before launch'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if campaign.status != 'draft':
            return Response({
                'error': f'Cannot launch campaign with status: {campaign.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        campaign.status = 'active'
        campaign.launched_at = timezone.now()
        campaign.save()
        
        return Response({
            'message': 'Campaign launched successfully',
            'data': CompanyMatchCampaignSerializer(campaign).data
        })
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause an active campaign"""
        campaign = self.get_object()
        company = self.get_company_from_campaign(campaign)
        
        if campaign.status != 'active':
            return Response({
                'error': f'Cannot pause campaign with status: {campaign.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        campaign.status = 'paused'
        campaign.save()
        
        return Response({
            'message': 'Campaign paused',
            'data': CompanyMatchCampaignSerializer(campaign).data
        })
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a paused campaign"""
        campaign = self.get_object()
        company = self.get_company_from_campaign(campaign)
        
        if campaign.status != 'paused':
            return Response({
                'error': f'Cannot resume campaign with status: {campaign.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        campaign.status = 'active'
        campaign.save()
        
        return Response({
            'message': 'Campaign resumed',
            'data': CompanyMatchCampaignSerializer(campaign).data
        })


class MatchingView(APIView):
    """
    Matching endpoints for donation flow.
    GET /api/matches/available/ - For donation flow
    POST /api/donations/{id}/match/ - Apply company match
    """
    authentication_classes = [TokenAuthentication]
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get(self, request):
        """GET /api/matches/available/ - Get available matches"""
        # Get active campaigns
        campaigns = CompanyMatchCampaign.objects.filter(
            status='active',
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now(),
            escrow_funded__gt=0
        ).select_related('company')
        
        # Filter by optional query params
        cause_id = request.query_params.get('cause')
        nonprofit_id = request.query_params.get('nonprofit')
        
        if cause_id:
            campaigns = campaigns.filter(eligible_causes__id=cause_id)
        if nonprofit_id:
            campaigns = campaigns.filter(
                Q(eligible_nonprofits__id=nonprofit_id) | 
                Q(eligible_nonprofits__isnull=True)
            )
        
        results = []
        for campaign in campaigns:
            results.append({
                'campaign_id': campaign.id,
                'campaign_name': campaign.name,
                'company_id': campaign.company.id,
                'company_name': campaign.company.name,
                'company_logo': campaign.company.logo,
                'match_multiplier': campaign.match_multiplier,
                'max_match_amount': campaign.max_match_per_donation,
                'remaining_budget': campaign.remaining_budget
            })
        
        serializer = AvailableMatchSerializer(data=results, many=True)
        serializer.is_valid()
        return Response(serializer.data)


class ApplyMatchView(APIView):
    """POST /api/donations/{id}/match/ - Apply company match to a donation"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, donation_id):
        donation = get_object_or_404(UserDonation, id=donation_id)
        
        # Verify user owns the donation
        if donation.user != request.user.profile:
            return Response({
                'error': 'You do not own this donation'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = MatchApplicationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        campaign_id = serializer.validated_data['campaign_id']
        campaign = get_object_or_404(CompanyMatchCampaign, id=campaign_id)
        
        # Validate campaign is active
        if campaign.status != 'active':
            return Response({
                'success': False,
                'message': f'Campaign is not active (status: {campaign.status})'
            })
        
        # Check if donation matches criteria
        if campaign.eligible_causes.exists():
            if not any(cat in donation.nonprofit.category.all() for cat in campaign.eligible_causes.all()):
                return Response({
                    'success': False,
                    'message': 'Donation does not match campaign cause criteria'
                })
        
        # Check minimum donation amount
        if campaign.min_donation_amount and donation.dollar_amount < campaign.min_donation_amount:
            return Response({
                'success': False,
                'message': f'Donation amount below minimum (${campaign.min_donation_amount})'
            })
        
        # Calculate match amount
        match_amount = donation.dollar_amount * campaign.match_multiplier
        if campaign.max_match_per_donation:
            match_amount = min(match_amount, campaign.max_match_per_donation)
        
        # Check remaining budget
        if match_amount > campaign.remaining_budget:
            match_amount = campaign.remaining_budget
        
        if match_amount <= 0:
            return Response({
                'success': False,
                'message': 'Campaign budget exhausted'
            })
        
        # Create match transaction
        CampaignEscrowTransaction.objects.create(
            campaign=campaign,
            transaction_type='match',
            amount=match_amount,
            donation=donation,
            description=f'Match for donation {donation.id}'
        )
        
        # Update campaign stats
        campaign.amount_matched += match_amount
        campaign.total_donations_matched += 1
        campaign.unique_donors = campaign.escrow_transactions.filter(
            transaction_type='match',
            donation__isnull=False
        ).values('donation__user').distinct().count()
        
        if campaign.amount_matched >= campaign.budget_cap:
            campaign.status = 'completed'
            campaign.completed_at = timezone.now()
        
        campaign.save()
        
        return Response({
            'success': True,
            'match_amount': match_amount,
            'message': f'Match of ${match_amount} applied successfully',
            'campaign': CompanyMatchCampaignListSerializer(campaign).data
        })


class RewardViewSet(viewsets.ModelViewSet):
    """
    Reward endpoints.
    GET /api/rewards/ - Public list
    GET /api/rewards/my/ - User's unlocked rewards
    POST /api/rewards/{id}/claim/ - Claim reward
    """
    queryset = CompanyReward.objects.all()
    serializer_class = CompanyRewardListSerializer
    authentication_classes = [TokenAuthentication]
    
    def get_permissions(self):
        if self.action in ['my', 'claim']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_queryset(self):
        queryset = CompanyReward.objects.filter(status='active')
        
        # Filter by availability
        now = timezone.now()
        queryset = queryset.filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now),
            Q(expiration_date__isnull=True) | Q(expiration_date__gt=now)
        )
        
        # Optional filters
        company_id = self.request.query_params.get('company')
        cause_id = self.request.query_params.get('cause')
        min_amount = self.request.query_params.get('min_amount')
        
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if cause_id:
            queryset = queryset.filter(specific_cause_id=cause_id)
        if min_amount:
            queryset = queryset.filter(min_donation_amount__lte=min_amount)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CompanyRewardSerializer
        return CompanyRewardListSerializer
    
    @action(detail=False, methods=['get'])
    def my(self, request):
        """GET /api/rewards/my/ - User's unlocked rewards"""
        claims = UserRewardClaim.objects.filter(
            user=request.user.profile
        ).select_related('reward', 'reward__company').order_by('-unlocked_at')
        
        serializer = UserRewardClaimSerializer(claims, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def claim(self, request, pk=None):
        """POST /api/rewards/{id}/claim/ - Claim reward"""
        reward = self.get_object()
        user = request.user.profile
        
        # Check if already claimed
        existing_claim = UserRewardClaim.objects.filter(
            user=user,
            reward=reward
        ).first()
        
        if existing_claim:
            return Response({
                'error': 'You have already claimed this reward'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check availability
        if not reward.is_available:
            return Response({
                'error': 'Reward is not available'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or assign reward code
        reward_code = None
        if reward.reward_type == 'digital':
            reward_code = CompanyRewardCode.objects.filter(
                reward=reward,
                is_claimed=False
            ).first()
            
            if not reward_code:
                return Response({
                    'error': 'No codes available for this reward'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate shipping for physical rewards
        shipping_address = request.data.get('shipping_address', '')
        if reward.shipping_required and not shipping_address:
            return Response({
                'error': 'Shipping address required for physical rewards'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create claim
        claim = UserRewardClaim.objects.create(
            user=user,
            reward=reward,
            status='claimed',
            reward_code=reward_code,
            shipping_address=shipping_address,
            claimed_at=timezone.now()
        )
        
        # Update reward code if assigned
        if reward_code:
            reward_code.is_claimed = True
            reward_code.claimed_by = user
            reward_code.claimed_at = timezone.now()
            reward_code.save()
        
        # Update reward stats
        reward.claimed_count += 1
        reward.save()
        
        return Response({
            'message': 'Reward claimed successfully',
            'data': UserRewardClaimSerializer(claim).data
        })


class CompanyRewardCodesView(APIView):
    """
    POST /api/companies/{id}/rewards/{reward_id}/codes/ - Bulk upload codes
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, company_id, reward_id):
        # Verify company ownership
        company = get_object_or_404(ForProfitCompany, id=company_id)
        if company.owner != request.user.profile:
            return Response({
                'error': 'You do not own this company'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Verify reward belongs to company
        reward = get_object_or_404(CompanyReward, id=reward_id, company=company)
        
        # Validate request
        serializer = CompanyRewardCodeBulkUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        codes = serializer.validated_data['codes']
        expires_at = serializer.validated_data.get('expires_at')
        
        # Create codes
        created_codes = []
        for code in codes:
            try:
                reward_code = CompanyRewardCode.objects.create(
                    reward=reward,
                    code=code,
                    expires_at=expires_at
                )
                created_codes.append(reward_code)
            except Exception as e:
                logger.error(f"Error creating reward code: {e}")
        
        return Response({
            'message': f'Successfully uploaded {len(created_codes)} codes',
            'total_codes': reward.codes.count(),
            'available_codes': reward.codes.filter(is_claimed=False).count()
        }, status=status.HTTP_201_CREATED)


class CompanyTierViewSet(viewsets.ModelViewSet):
    """Admin endpoint for managing company tiers"""
    queryset = CompanyTier.objects.all()
    serializer_class = CompanyTierSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]


class CompanyInvoiceAdminViewSet(viewsets.ModelViewSet):
    """Admin endpoint for managing company invoices"""
    queryset = CompanyInvoice.objects.all()
    serializer_class = CompanyInvoiceSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]
