
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Donation, Donor, NonProfitRequest, PointTransaction, RequestVotes, User, UserProfile, Balance, CompanyMatchDonation
from api.models import AltruePoints, Link, UserDonation


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password','username')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name','profile_created')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('pk','email', 'first_name', 'last_name', 'is_staff', 'profile_created','altrue_level','registered_with_code',)
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-pk',)
    

class ProfileAdmin(admin.ModelAdmin):
    model = UserProfile
    list_display = ('pk','username','account_balance','completed_altrue_actions_count','altrue_level','altrue_points','stripe_customer_id')
    
    def account_balance(self, obj):
        if obj.balance.balance is None:
            return 'Not Created'
        return'$ {}'.format(obj.balance.balance)
    
    def altrue_points(self,obj):
        if obj.altrue_points is None:
            return 'Not Created'
        return obj.altrue_points
    
    def completed_altrue_actions_count(self, obj):
        return obj.completed_altrue_actions_count
        

admin.site.register(UserProfile, ProfileAdmin)

    
class DonorAdmin(admin.ModelAdmin):
    model = Donor
    fields = ('email', 'last_name', 'amount_donated', 'sent_to', 'first_name','donation_category')
    list_display = ('email', 'last_name', 'amount_donated', 'sent_to', 'first_name','donor_code')


admin.site.register(NonProfitRequest)

admin.site.register(RequestVotes)




class BalanceAdmin(admin.ModelAdmin):
    model = Balance
    fields = ('account', 'balance')
    list_display =('account', 'balance', 'last_transaction')

class DonationAdmin(admin.ModelAdmin):
    model = Donation
    fields= ('donor',)
    
    list_display = ('donor','donation_date','donation_amount', 'receiver')


class AltruePointsAdmin(admin.ModelAdmin):
    model = AltruePoints
    fields=('account', 'balance',)

    list_display = ('account', 'balance', 'last_transaction')



admin.site.register(Donor, DonorAdmin)
admin.site.register(Balance, BalanceAdmin)
admin.site.register(Donation, DonationAdmin)
admin.site.register(AltruePoints, AltruePointsAdmin)


class UserDonationAdmin(admin.ModelAdmin):
    list_display = ('pk' ,'user', 'dollar_amount', 'nonprofit', 'atrocity','project')
    
admin.site.register(UserDonation, UserDonationAdmin)

class CompanyMatchAdmin(admin.ModelAdmin):
    list_display = ('company','donation_date','nonprofit', 'atrocity','transaction_matched','amount')
    model= CompanyMatchDonation
admin.site.register(CompanyMatchDonation, CompanyMatchAdmin)




class LinkAdmin(admin.ModelAdmin):
    list_display = [ 'publication', 'atrocity', 'nonprofit','company']
    model = Link

    
admin.site.register(Link, LinkAdmin)


class PointTransactionAdmin(admin.ModelAdmin):
    list_display =['user','action','amount','timestamp']
    model = PointTransaction

admin.site.register(PointTransaction, PointTransactionAdmin)


