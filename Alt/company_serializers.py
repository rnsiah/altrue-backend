from rest_framework import serializers
from Alt.models import (
    CompanyTier, CompanyWallet, CompanyApplication, CompanyMatchCampaign,
    CampaignEscrowTransaction, CompanyInvoice, CompanyReward, CompanyRewardCode,
    UserRewardClaim, WalletTransaction, ForProfitCompany, NonProfit
)
from api.models import UserDonation, UserProfile


# Simple serializers to avoid circular imports
class CompanyRepSerializer(serializers.ModelSerializer):
    """Simple company representation"""
    class Meta:
        model = ForProfitCompany
        fields = ['id', 'name', 'logo']


class NonProfitRepSerilizer(serializers.ModelSerializer):
    """Simple nonprofit representation"""
    class Meta:
        model = NonProfit
        fields = ('id', 'logo', 'name')


class ProfileRepSerializer(serializers.ModelSerializer):
    """Simple profile representation"""
    id = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = ['username', 'id', 'profile_picture']
    
    def get_id(self, obj):
        return obj.pk
    
    def get_profile_picture(self, obj):
        return None  # Simplified for now


class UserDonationSerializer(serializers.ModelSerializer):
    """Simplified donation serializer"""
    user = ProfileRepSerializer(read_only=True)
    
    class Meta:
        model = UserDonation
        fields = ('id', 'dollar_amount', 'nonprofit', 'atrocity', 'project', 'user', 'donation_date')


class ForProfitCompanySerializer(serializers.ModelSerializer):
    """Simplified company serializer"""
    owner = ProfileRepSerializer(read_only=True)
    
    class Meta:
        model = ForProfitCompany
        fields = ['id', 'name', 'logo', 'description', 'mission', 'website_address', 'owner']


class CompanyTierSerializer(serializers.ModelSerializer):
    """Serializer for CompanyTier model"""
    tier_display = serializers.CharField(source='get_tier_display', read_only=True)
    
    class Meta:
        model = CompanyTier
        fields = [
            'id', 'company', 'tier', 'tier_display', 'monthly_fee',
            'transaction_fee_percent', 'stripe_subscription_id', 'stripe_customer_id',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['monthly_fee', 'transaction_fee_percent', 'created_at', 'updated_at']


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer for WalletTransaction model"""
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'wallet', 'transaction_type', 'transaction_type_display',
            'amount', 'description', 'stripe_payment_intent_id',
            'matched_donation', 'created_at'
        ]
        read_only_fields = ['created_at']


class CompanyWalletSerializer(serializers.ModelSerializer):
    """Serializer for CompanyWallet model"""
    transactions = WalletTransactionSerializer(many=True, read_only=True)
    remaining_budget = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    can_match = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CompanyWallet
        fields = [
            'id', 'company', 'balance', 'monthly_budget', 'matched_this_month',
            'remaining_budget', 'auto_pause_threshold', 'auto_refill_enabled',
            'auto_refill_threshold', 'auto_refill_amount', 'is_active', 'is_paused',
            'paused_at', 'pause_reason', 'can_match', 'transactions',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'balance', 'matched_this_month', 'is_paused', 'paused_at', 'pause_reason',
            'created_at', 'updated_at'
        ]


class CompanyWalletSimpleSerializer(serializers.ModelSerializer):
    """Simplified wallet serializer for list views"""
    remaining_budget = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = CompanyWallet
        fields = ['id', 'balance', 'monthly_budget', 'matched_this_month', 'remaining_budget', 'is_active', 'is_paused']


class CompanyApplicationSerializer(serializers.ModelSerializer):
    """Serializer for CompanyApplication model"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_company = ForProfitCompanySerializer(read_only=True)
    
    class Meta:
        model = CompanyApplication
        fields = [
            'id', 'company_name', 'ein', 'website', 'mission_statement', 'description',
            'annual_matching_commitment', 'contact_name', 'contact_email', 'contact_phone',
            'street_address', 'city', 'state', 'zip_code', 'country', 'logo_url',
            'status', 'status_display', 'applied_at', 'reviewed_at', 'reviewed_by',
            'rejection_reason', 'notes', 'approved_company', 'ein_verified'
        ]
        read_only_fields = [
            'status', 'applied_at', 'reviewed_at', 'reviewed_by', 'rejection_reason',
            'notes', 'approved_company', 'ein_verified', 'ein_verification_data'
        ]


class CompanyApplicationAdminSerializer(serializers.ModelSerializer):
    """Serializer for admin review of applications"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CompanyApplication
        fields = '__all__'
        read_only_fields = ['applied_at', 'reviewed_at']


class CampaignEscrowTransactionSerializer(serializers.ModelSerializer):
    """Serializer for CampaignEscrowTransaction model"""
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    donation = UserDonationSerializer(read_only=True)
    
    class Meta:
        model = CampaignEscrowTransaction
        fields = [
            'id', 'campaign', 'transaction_type', 'transaction_type_display',
            'amount', 'description', 'donation', 'stripe_payment_intent_id', 'created_at'
        ]
        read_only_fields = ['created_at']


class CompanyMatchCampaignSerializer(serializers.ModelSerializer):
    """Serializer for CompanyMatchCampaign model"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    company = ForProfitCompanySerializer(read_only=True)
    company_id = serializers.IntegerField(write_only=True)
    remaining_budget = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_fully_funded = serializers.BooleanField(read_only=True)
    escrow_remaining = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = CompanyMatchCampaign
        fields = [
            'id', 'company', 'company_id', 'name', 'description', 'slug',
            'match_multiplier', 'max_match_per_donation', 'start_date', 'end_date',
            'budget_cap', 'required_escrow', 'escrow_funded', 'amount_matched',
            'remaining_budget', 'is_fully_funded', 'escrow_remaining',
            'eligible_causes', 'eligible_nonprofits', 'min_donation_amount',
            'status', 'status_display', 'shirt_sponsorship_enabled',
            'sponsor_logo_placement', 'sponsor_shirt', 'total_donations_matched',
            'unique_donors', 'created_at', 'updated_at', 'launched_at', 'completed_at'
        ]
        read_only_fields = [
            'slug', 'required_escrow', 'escrow_funded', 'amount_matched',
            'total_donations_matched', 'unique_donors', 'created_at', 'updated_at',
            'launched_at', 'completed_at'
        ]


class CompanyMatchCampaignListSerializer(serializers.ModelSerializer):
    """Simplified campaign serializer for list views"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    company = CompanyRepSerializer(read_only=True)
    
    class Meta:
        model = CompanyMatchCampaign
        fields = [
            'id', 'company', 'name', 'slug', 'match_multiplier',
            'start_date', 'end_date', 'budget_cap', 'amount_matched',
            'status', 'status_display', 'shirt_sponsorship_enabled'
        ]


class CampaignFundSerializer(serializers.Serializer):
    """Serializer for funding campaign escrow"""
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    stripe_payment_intent_id = serializers.CharField(required=True)


class CompanyInvoiceSerializer(serializers.ModelSerializer):
    """Serializer for CompanyInvoice model"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    company = ForProfitCompanySerializer(read_only=True)
    
    class Meta:
        model = CompanyInvoice
        fields = [
            'id', 'company', 'month', 'monthly_fee', 'total_matched',
            'transaction_fee_percent', 'altrue_fee', 'total_due',
            'status', 'status_display', 'stripe_invoice_id', 'stripe_payment_intent_id',
            'created_at', 'paid_at'
        ]
        read_only_fields = [
            'monthly_fee', 'total_matched', 'transaction_fee_percent',
            'altrue_fee', 'total_due', 'created_at', 'paid_at'
        ]


class CompanyRewardCodeSerializer(serializers.ModelSerializer):
    """Serializer for CompanyRewardCode model"""
    claimed_by = ProfileRepSerializer(read_only=True)
    
    class Meta:
        model = CompanyRewardCode
        fields = [
            'id', 'reward', 'code', 'is_claimed', 'claimed_by', 'claimed_at',
            'expires_at', 'is_redeemed', 'redeemed_at', 'created_at'
        ]
        read_only_fields = ['is_claimed', 'claimed_by', 'claimed_at', 'is_redeemed', 'redeemed_at', 'created_at']


class CompanyRewardSerializer(serializers.ModelSerializer):
    """Serializer for CompanyReward model"""
    reward_type_display = serializers.CharField(source='get_reward_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    company = ForProfitCompanySerializer(read_only=True)
    company_id = serializers.IntegerField(write_only=True, required=False)
    remaining_quantity = serializers.IntegerField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    codes_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CompanyReward
        fields = [
            'id', 'company', 'company_id', 'name', 'description', 'reward_type',
            'reward_type_display', 'image_url', 'min_donation_amount', 'min_altrue_level',
            'min_streak_days', 'specific_cause', 'specific_nonprofit', 'campaign',
            'total_quantity', 'claimed_count', 'remaining_quantity', 'shipping_required',
            'estimated_delivery_days', 'code_prefix', 'start_date', 'expiration_date',
            'status', 'status_display', 'views_count', 'codes_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'claimed_count', 'views_count', 'created_at', 'updated_at'
        ]
    
    def get_codes_count(self, obj):
        return obj.codes.count()


class CompanyRewardListSerializer(serializers.ModelSerializer):
    """Simplified reward serializer for list views"""
    reward_type_display = serializers.CharField(source='get_reward_type_display', read_only=True)
    company = CompanyRepSerializer(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CompanyReward
        fields = [
            'id', 'company', 'name', 'description', 'reward_type', 'reward_type_display',
            'image_url', 'min_donation_amount', 'remaining_quantity', 'is_available'
        ]


class CompanyRewardCodeBulkUploadSerializer(serializers.Serializer):
    """Serializer for bulk uploading reward codes"""
    codes = serializers.ListField(
        child=serializers.CharField(max_length=255),
        allow_empty=False
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class UserRewardClaimSerializer(serializers.ModelSerializer):
    """Serializer for UserRewardClaim model"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reward = CompanyRewardListSerializer(read_only=True)
    reward_code = CompanyRewardCodeSerializer(read_only=True)
    unlocked_by_donation = UserDonationSerializer(read_only=True)
    
    class Meta:
        model = UserRewardClaim
        fields = [
            'id', 'user', 'reward', 'status', 'status_display', 'reward_code',
            'shipping_address', 'tracking_number', 'shipped_at', 'delivered_at',
            'unlocked_by_donation', 'unlocked_at', 'viewed_at', 'claimed_at', 'redeemed_at',
            'notification_sent', 'reminder_sent'
        ]
        read_only_fields = [
            'user', 'reward', 'status', 'reward_code', 'unlocked_by_donation',
            'unlocked_at', 'viewed_at', 'claimed_at', 'redeemed_at',
            'notification_sent', 'reminder_sent'
        ]


class UserRewardClaimCreateSerializer(serializers.Serializer):
    """Serializer for claiming a reward"""
    shipping_address = serializers.CharField(required=False, allow_blank=True)


class CompanyDashboardSerializer(serializers.Serializer):
    """Serializer for company dashboard stats"""
    company = ForProfitCompanySerializer()
    tier = CompanyTierSerializer()
    wallet = CompanyWalletSimpleSerializer()
    
    # Stats
    total_campaigns = serializers.IntegerField()
    active_campaigns = serializers.IntegerField()
    total_matched_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_matched_all_time = serializers.DecimalField(max_digits=12, decimal_places=2)
    unique_donors_reached = serializers.IntegerField()
    
    # Rewards stats
    total_rewards = serializers.IntegerField()
    active_rewards = serializers.IntegerField()
    total_claims = serializers.IntegerField()
    
    # Recent activity
    recent_campaigns = CompanyMatchCampaignListSerializer(many=True)
    recent_invoices = CompanyInvoiceSerializer(many=True)


class AvailableMatchSerializer(serializers.Serializer):
    """Serializer for available company matches"""
    campaign_id = serializers.IntegerField()
    campaign_name = serializers.CharField()
    company_id = serializers.IntegerField()
    company_name = serializers.CharField()
    company_logo = serializers.CharField()
    match_multiplier = serializers.DecimalField(max_digits=3, decimal_places=1)
    max_match_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    remaining_budget = serializers.DecimalField(max_digits=12, decimal_places=2)


class MatchApplicationSerializer(serializers.Serializer):
    """Serializer for applying a match to a donation"""
    campaign_id = serializers.IntegerField(required=True)
    donation_id = serializers.IntegerField(required=True)


class CompanyMatchResultSerializer(serializers.Serializer):
    """Serializer for match application result"""
    success = serializers.BooleanField()
    match_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    message = serializers.CharField()
    campaign = CompanyMatchCampaignListSerializer(required=False)
