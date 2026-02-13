from django.contrib import admin
from django.utils.html import mark_safe

from django.contrib import messages

from api.helpers import create_printful_order
from api.models import Post, PostAttachment
from .models import  AltrueActionOnAggregate, AltrueActionType, AltruePointPromotion, AtrocityDonation, CompanyBalance, Mockup,CompanyDonation, CompanyProjectRelationShip, NonProfitAtrocityRelationShip, NonProfitDonation, NonProfitProject, CompanyAtrocityRelationship, CompanyNonProfitRelationship ,AtrocityShirt, NonProfitProjectDonation, Quiz, QuizAnswers, QuizQuestion, QuizResult, Shirt, Atrocity, Category, NonProfit, Country, Rating, Order, OrderItem, CheckoutAddress, CompanyCoupon, CompanyStore, ForProfitCompany, AltrueAction, AltrueLevel, ShirtColor, ShirtGroup, ShirtSize, ShirtVariations, UserAltrueAction, FriendInvite, AltrueActionCode, ProfileImage, UserMatchRelationShip, UserMatchTransaction
from Alt.models import AtrocityBalance, NonProfitBalance


class ShirtAdmin(admin.ModelAdmin):
    list_display =('id','name',)
    prepopulated_fields = {'slug': ('name',)} 

admin.site.register(Shirt, ShirtAdmin)


class AtrueActionOnAggregateAdmin(admin.ModelAdmin):
    list_display =('altrue_action','aggregate_action')

admin.site.register(AltrueActionOnAggregate, AtrueActionOnAggregateAdmin)




class NonProfitDonationAdmin(admin.ModelAdmin):
    list_display=('id','profile_donated', 'nonprofit','donation_date','donation_amount')   
admin.site.register(NonProfitDonation, NonProfitDonationAdmin)

class AtrocityDonationAdmin(admin.ModelAdmin):
    list_display = ('id','profile_donated','atrocity','donation_date', 'donation_amount')
admin.site.register(AtrocityDonation, AtrocityDonationAdmin)

class NonProfitProjectDonationAdmin(admin.ModelAdmin):
    list_display=('id','profile_donated','nonprofit','project','donation_date')
admin.site.register(NonProfitProjectDonation)


admin.site.register(ShirtVariations)

class NonProfitAdmin(admin.ModelAdmin):
    list_display = ('id','name',)
    prepopulated_fields = {'slug': ('name',)} 

admin.site.register(NonProfit, NonProfitAdmin)

# Register your models here.


admin.site.register(ShirtColor)

class ShirtDisplayAdmin(admin.ModelAdmin):
    list_display = ['get_size_display']

class OrderAdmin(admin.ModelAdmin):
    list_display = ('user','start_date','completed','paid_for')

admin.site.register(UserMatchTransaction)
admin.site.register(QuizAnswers)
admin.site.register(QuizQuestion)
admin.site.register(Quiz)


admin.site.register(ShirtSize, ShirtDisplayAdmin)
admin.site.register(Atrocity)
admin.site.register(Category)
admin.site.register(AtrocityShirt)

admin.site.register(Country)
admin.site.register(Rating)
admin.site.register(ShirtGroup)

admin.site.register(Order,OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(CheckoutAddress)
admin.site.register(AltrueActionCode)

admin.site.register(Post)
admin.site.register(PostAttachment)


class NonProfitBalanceAdmin(admin.ModelAdmin):
    list_display = ('id','nonprofit', 'balance',)

admin.site.register(NonProfitBalance, NonProfitBalanceAdmin)

class AtrocityBalanceAdmin(admin.ModelAdmin):
    list_display = ('atrocity', 'balance','last_transaction' )
    model = AtrocityBalance
admin.site.register(AtrocityBalance, AtrocityBalanceAdmin)



admin.site.register(QuizResult)
admin.site.register(FriendInvite)


admin.site.register(CompanyProjectRelationShip)

class AltrueActionTypeAdmin(admin.ModelAdmin):
    list_display =('code','description')
    model = AltrueActionType
admin.site.register(AltrueActionType, AltrueActionTypeAdmin)

class CompanyAdmin(admin.ModelAdmin):
    list_display=('id','name')
admin.site.register(ForProfitCompany, CompanyAdmin)

admin.site.register(CompanyCoupon)

admin.site.register(CompanyStore)

class CompanyDonationAdmin(admin.ModelAdmin):
    list_display = ('company', 'amount', 'nonprofit', 'atrocity')

admin.site.register(CompanyDonation, CompanyDonationAdmin)

class CompanyBalanceAdmin(admin.ModelAdmin):
    list_display = ('id','company', 'balance')

admin.site.register(CompanyBalance, CompanyBalanceAdmin)

class NonProfitProjectAdmin(admin.ModelAdmin):
    list_display =('id','nonprofit', 'title')

admin.site.register(NonProfitProject, NonProfitProjectAdmin)
admin.site.register(NonProfitAtrocityRelationShip)

class CompanyAtroRelationshipAdmin(admin.ModelAdmin):
    list_display = ('company', 'atrocity', 'total_raised')
admin.site.register(CompanyAtrocityRelationship, CompanyAtroRelationshipAdmin)

class CompanyNPRelationshipAdmin(admin.ModelAdmin):
    list_display = ('company', 'nonprofit', 'total_raised')
admin.site.register(CompanyNonProfitRelationship, CompanyNPRelationshipAdmin)

class UserMatchRelationShipAdmin(admin.ModelAdmin):
    list_display = ('user_matching_donation','user_being_matched', )
admin.site.register(UserMatchRelationShip, UserMatchRelationShipAdmin)

class AltrueLevelAdmin(admin.ModelAdmin):
    list_display = ('level_number', 'name','minimum_points', 'maximum_points')
admin.site.register(AltrueLevel, AltrueLevelAdmin)

class UserActionAdmin(admin.ModelAdmin):
    model = UserAltrueAction
    list_display = ('profile_acting','altrue_action','points','date_completed', )
    
    def points(self, obj):
        action = obj.altrue_action

        try:
            love = AltrueAction.objects.get(pk = action.pk)
            if love.is_promoted ==True:
                total = love.points_awarded * love.promotion.multiplier
                return total
            return love.points_awarded
        except love.DoesNotExist:
            return 0


admin.site.register(UserAltrueAction, UserActionAdmin)


class AltruePointPromotionAdmin(admin.ModelAdmin):
    model = AltruePointPromotion
    
    list_display = ('name','is_active','start_date','end_date','actions_promoted')

    def actions_promoted(self, obj):
        li = []
        love = list(AltrueAction.objects.filter(promotion =obj))
        for lo in love:
            li.append({lo.id:lo.requirement})
        return li

admin.site.register(AltruePointPromotion, AltruePointPromotionAdmin)


class AltrueActionAdmin(admin.ModelAdmin):
    model = AltrueAction
    list_display = ('id','requirement', 'needed_to_pass', 'points_awarded','code')
    
    def needed_to_pass(self, obj):
        level1 = AltrueLevel.objects.get(level_number =1)
        level2 = AltrueLevel.objects.get(level_number =2)
        if obj in level1.requiredActions.all():
            return "Level 0"
        elif obj in level2.requiredActions.all():
            return "Level 1"
        return 'No Level'
        
    def code(self, obj):
        return obj.action_code


admin.site.register(AltrueAction, AltrueActionAdmin)


class ProfileImageAdmin(admin.ModelAdmin):
    model =ProfileImage
    list_display =('profile_id', 'profile') 
    ordered=('profile_id',)
admin.site.register(ProfileImage, ProfileImageAdmin)



def create_draft_order(modeladmin, request, queryset):
    proocessed_order_item = set()
    for mockup in queryset:
        order_item = mockup.order_item
        order = order_item.order_set.first()
        print(order)
        if all(m.verified for m in order.mockups_for_order.all()):
            messages.success(request, f"All mockups verified for order {order.id}")

            # Call create_printful_order and handle potential errors
            draft_id = create_printful_order(order)
            print(draft_id)
            if draft_id:
                order.fullfillment_started = True  # Use draft_created instead of fulfillment_started
                order.fullfillment_id = draft_id
                order.save()
                messages.success(request, f"Draft order created for order {order.id}")
            else:
                messages.error(request, f"Error creating draft order for order {order.id}")
        else:
            messages.error(request, f"Not all mockups are verified for order {order.id}")

create_draft_order.short_description = 'Create Draft Order'

 


class MockupAdmin(admin.ModelAdmin):
    list_display = ("order_item", "display_mockup_image", 'verified', 'order_id')
    list_editable = ['verified']
    actions = [create_draft_order ]

    def order_id(self, obj):
        order_items= obj.order_item.order_set.all()
        if order_items:
            return order_items.first().id
        else:
            return None
    
    

    def display_mockup_image(self, obj):
        if obj.url:
            return mark_safe(
                f'<img src="{obj.url}" style="max-width:100px; max-height:100px;" />'
            )
        else:
            return "No Image"

    display_mockup_image.short_description = "Mockup Image"


admin.site.register(Mockup, MockupAdmin)