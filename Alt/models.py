from email.policy import default
from tabnanny import verbose
from xmlrpc.client import Boolean
from django.db import models, transaction
from allauth.account.signals import email_confirmed
from django.core.mail import EmailMultiAlternatives
from django.dispatch import Signal
from django.template.loader import get_template
from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models.signals import m2m_changed
from django.db.models.deletion import CASCADE
from django.db.models.fields import CharField, IntegerField
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField
from django.dispatch.dispatcher import receiver
from django.shortcuts import reverse
from django_countries.fields import CountryField
from django.template.defaultfilters import slugify
from django.db.models.signals import post_delete, post_save, pre_save
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ObjectDoesNotExist
import random
import string
from django.apps import apps
from django.utils import timezone
from random import randint

from api.helpers import find_variant, generate_mockups_for_order


class ProfileImage(models.Model):
    """
    Model representing a user's profile image.
    """

    profile = models.OneToOneField("api.UserProfile",  on_delete=models.CASCADE,  related_name ='profile_pic', blank = True, primary_key = True)
    image = models.ImageField(upload_to= 'media_root/profiles', default ='default.png')

    @property
    def image_url(self):
        if self.image:
            return f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/media_root/{self.image.name}'
        return None
    
    def __str__(self):
        return self.profile.user.email + "'s profile picture"


class Country(models.Model):

    """
    Model representing a country.
    """
    name= models.CharField( max_length=50, blank=False, null=False)
    flag =models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.name

class AltrueActionCode(models.Model):

    """
    Model representing an Altrue action code.
    """
    code= models.CharField(max_length=50, blank= True, null= True)

    def __str__(self):
        return self.code


class AltrueActionType(models.Model):
    
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.code

class AltrueAction(models.Model):

    """
    Model representing an Altrue action.
    """

    requirement = models.TextField()
    info = models.TextField(blank=True, null=True)
    points_awarded = models.IntegerField(blank = True, null = True)
    number_of_occurrences = models.IntegerField(blank = True, null=True)
    action_type = models.ForeignKey(AltrueActionType, on_delete=models.CASCADE, null=True, blank=True)
    action_code = models.ForeignKey('Alt.AltrueActionCode', on_delete=models.CASCADE, blank = True, null = True)
    is_promoted = models.BooleanField(default=False)
    promotion = models.ForeignKey("Alt.AltruePointPromotion", on_delete=models.CASCADE, blank = True, null = True )
    is_aggregate_action = models.BooleanField(default=False)
    aggregate_count = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.requirement
    

class UserAggregateAction(models.Model):
    
    user = models.ForeignKey('api.UserProfile', on_delete=models.CASCADE)
    aggregate_action = models.ForeignKey(AltrueAction, on_delete=models.CASCADE)
    count = models.IntegerField(default=0)

class UserAltrueAction(models.Model):
    """
    Model representing a user's completed Altrue action.
    """
    
    profile_acting = models.ForeignKey("api.UserProfile", on_delete=models.CASCADE)
    altrue_action = models.ForeignKey('Alt.AltrueAction', blank=True, null=True, on_delete=models.CASCADE)
    date_completed = models.DateField(auto_now_add=True)
    is_promotion = models.BooleanField(default = False)
    is_aggregate = models.BooleanField(default=False)
    count = models.IntegerField(default=0, blank=True, null=True)
    aggregate_complete_date = models.DateField(null=True, blank=True)
    point_transaction = models.ForeignKey('api.PointTransaction', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        if self.altrue_action is None:
            return 'awarded to {} for ?'.format(self.profile_acting)
        return  ' awarded to {} for {}'.format(self.profile_acting.user.email, self.altrue_action.requirement)

class AltrueActionOnAggregate(models.Model):
    altrue_action = models.ForeignKey(AltrueAction, on_delete=models.CASCADE, related_name='aggregate_actions')
    aggregate_action = models.ForeignKey(AltrueAction, on_delete=models.CASCADE,related_name='aggregate_of')


class AltruePointPromotion(models.Model):
    """
    Model representing an Altrue point promotion.
    """

    POINT_PROMOTION_INCREASE =(
        (2, 'Double'),
        (3, 'Triple'),

    )
    DONATION_INCREASE=(
        (10, 'Ten Percent'),
        (20, 'Twenty Percent'),
        (50, 'Fifty Percent'),
        (100, 'One Hundred Percent')
    )
    multiplier  = models.IntegerField(choices=POINT_PROMOTION_INCREASE, null = True, blank= True )
    name = models.CharField(max_length = 50, null= True, blank = True)
    description= models.TextField(blank= True, null= True)
    donation_increase = models.IntegerField(choices= DONATION_INCREASE, null = True, blank=True)
    is_active = models.BooleanField(default=False)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)


    def __str__(self):
        return self.name

class PointSystemConversionRate(models.Model):
    rate_value = models.DecimalField(max_digits=6, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return str(self.rate_value)


class AltrueLevel(models.Model):

    """
    Model representing an Altrue level.
    """

    level_number = models.IntegerField(blank=True, null= True)
    name = models.CharField(max_length=50, blank=False, null= False)
    requiredActions = models.ManyToManyField(AltrueAction, blank=True)
    minimum_points = models.IntegerField(blank = False, null= False )
    maximum_points = models.IntegerField(blank = False, null = False)
    conversion_multiplier = models.DecimalField(max_digits=10, decimal_places=2, blank =True, null=True)

    def __str__(self):
        return self.name


class FriendInvite(models.Model):

    """
    Model representing a friend invitation.
    """
    inviter = models.OneToOneField('api.UserProfile', on_delete=models.CASCADE, blank=True, null= True)
    invited = models.CharField(blank= False, null= False, max_length= 50)
    invite_code = models.CharField(max_length= 8, blank=True, null=True)
    completed = models.BooleanField(default= False)
    invite_date = models.DateTimeField(auto_now_add=True)
    action = models.ForeignKey('Alt.AltrueActionCode',  on_delete=models.CASCADE, blank=True, null=True)


    def __str__(self):
        return ' invited ' +self.invited


    def create_code(self):
        letters = string.ascii_letters
        randomized = ( ''.join(random.choice(letters) for i in range(7)) )
        self.invite_code = randomized


    def save(self, *args, **kwargs):
       self.create_code()

       super(FriendInvite, self).save(*args, **kwargs) # Call the real save() method


class Category(models.Model):
    """
    Model representing a category.
    """
    name = models.CharField(max_length = 50, blank=False, )
    image = models.CharField(max_length=500)
    information =models.TextField()
    blurb = models.TextField(null=True, blank=True)


    def __str__(self):
        return self.name


class AtrocityShirt(models.Model):

    """
    Model representing an Atrocity shirt.
    """

    name = models.CharField(max_length=30, blank=False, null=False)
    price = models.FloatField()
    discount_price = models.FloatField(blank= True, null=True)
    shirt_type = models.CharField(max_length=30)
    country = models.ForeignKey('Alt.Country', on_delete=models.CASCADE)
    shirt_image = models.CharField( max_length=150)
    original_image = models.CharField(max_length =150)
    slug = models.SlugField(unique = True, null=True, blank=True)
    featured = models.BooleanField(blank=True, null=True)
    date_added= models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.name
    def slug(self):
        return slugify(self.name)


class Atrocity(models.Model):

    """
    Model representing an atrocity.
    """
    title = models.CharField(max_length=100, blank=False, null=False)
    region = models.CharField(max_length=30, blank=False, null=False)
    info= models.TextField()
    image_url = models.TextField()
    category = models.ManyToManyField('Alt.Category', blank=True, related_name='atrocity')
    country = models.ForeignKey('Alt.Country', on_delete=models.CASCADE,blank=True, null=True )
    slug = models.SlugField(unique = True)
    featured= models.BooleanField(blank = False, null = False, default=False)
    date_added= models.DateTimeField( auto_now_add=True)
    videoURL= models.URLField( max_length=200)



    @property
    def total_balance(self):
        return self.balance.balance


    @property
    def atrocity_shirt_list(self):
        category = self.category.all()
        for categories in category:
           return categories.shirt.all()

    # find the nonprofits associated with the category of the atrocity, but exclude nonprofits associated with atrocity
    @property
    def np_list(self):
        category= self.category.all()
        np = []
        for categories in category:
            nps = categories.NonProfit.all()
            return nps


    def __str__(self):
        return self.title
    def slug(self):
        return slugify(self.title)

    def get_absolute_url(self):
        return reverse ('Alt:Atrocity', kwargs={'slug':self.slug})

    def get_categories(self):
        return Atrocity.objects.filter(category__id =self.id)


class ShirtSize(models.Model):

    """
    Model representing a shirt size.
    """

    SHIRT_SIZE = (
    (1, 'XS'),
    (2, 'S'),
    (3, 'M'),
    (4, 'L'),
    (5, 'XL'),
    (6, 'XXL')

    )

    size = models.IntegerField(choices= SHIRT_SIZE, blank = False, null = False)

    def __str__(self):
        return str(self.size)


class ShirtGroup(models.Model):

    """
    Model representing a shirt group.
    """

    name= models.TextField()
    description = models.TextField()
    creator = models.CharField(max_length=150,blank=True, null=True)
    groupImage = models.CharField(max_length=150)
    altrue_level= models.ForeignKey(AltrueLevel, blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class ShirtColor(models.Model):
    """
    Model representing a shirt color.
    """

    color = models.CharField( max_length=50)
    hex_code = models.CharField(max_length= 10, blank=True, null=True)

    def __str__(self):
        return self.color


class ShirtVariations(models.Model):
    """
    Model representing shirt variations.
    """

    image = models.CharField(max_length=150, null = True, blank = True)
    back_image =models.CharField(max_length=150, blank=True, null=True)
    color = models.ForeignKey(ShirtColor, on_delete=models.CASCADE)
    shirt = models.ForeignKey("Alt.Shirt", on_delete=models.CASCADE, blank = True, null=True)

    def __str__(self):
        return self.shirt.name + ' ' + self.color.color


class Shirt(models.Model):

    """
    Model representing a shirt.
    """
    product_unique_id= models.CharField(blank= True, max_length=100)
    quantity_limited = models.BooleanField(blank= False, null= False)
    total_quantity = models.IntegerField(blank=True,null = True)
    name = models.CharField(max_length=30, blank=False, null=False)
    price = models.FloatField()
    points_needed_to_purchase= models.IntegerField(blank=False, null=False)
    available_colors = ManyToManyField(ShirtColor, blank= True)
    available_sizes = ManyToManyField(ShirtSize, blank = True)
    discount_price = models.FloatField()
    shirt_type = models.CharField(max_length=30, blank=False, null=False)
    country = models.ForeignKey('Alt.Country', on_delete=models.CASCADE, blank=True, null=True)
    shirt_image = models.CharField( max_length=150)
    original_image = models.CharField(max_length =150)
    slug = models.SlugField(unique = True, null=True, blank=True)
    featured = models.BooleanField(blank = False, null=False, default=False)
    date_added= models.DateTimeField(auto_now_add=True)
    category = ForeignKey('Alt.Category', blank= True, on_delete=models.CASCADE, related_name='shirt')
    altrue_story = models.TextField(blank = True, null=True)
    shirt_group = models.ForeignKey('Alt.ShirtGroup', on_delete=models.CASCADE, blank=True, null=True)
    required_level = models.ForeignKey(AltrueLevel, blank =True, null = True, on_delete=models.CASCADE)
    shirt_style= models.TextField(blank=True, null= False)
    shirt_materials= models.TextField(blank=True, null= False)
    shirt_back_image = models.CharField(blank=True, null=True, max_length=150)
    shirt_image_front_file = models.CharField(blank= True, null= True, max_length=150)
    shirt_image_back_file= models.CharField(blank=True, null=True,max_length=150)
    printful_id = models.CharField(blank=True, null = True, max_length=150)

    @property
    def similar_shirts(self):
        cat = self.category
        return Shirt.objects.filter(category = cat).exclude(id= self.id)

    @property
    def atrocityList(self):
        cat = self.category
        return Atrocity.objects.filter(category = cat)


    def __str__(self):
        return self.name



    def addToCart(self):
        return reverse('core: add-to-cart', kwargs={
            'slug':self.slug
        })


    def removeFromCart(self):
        return reverse( 'core: remove-from-cart', kwargs={
            'slug':self.slug
        })


    def get_absolute_url(self):
        return reverse("Alt:shirts", kwargs={"slug": self.slug})

    def no_of_ratings(self):
        ratings = Rating.objects.filter(shirt =self)
        return len(ratings)

    def average_rating(self):
        sum = 0
        ratings = Rating.objects.filter(shirt =self)
        for rating in ratings:
            sum += rating.stars
        if len(ratings) > 0:
            return sum /len(ratings)
        else:
            return 0

    def get_categories(self):
        return Shirt.objects.filter(category__id =self.id)

    def save(self,*args, **kwargs):
        if not self.product_unique_id:
            self.product_unique_id=f"{self.name}"
        super().save(*args, **kwargs)

def slug_generator(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug='SLUG'

pre_save.connect(slug_generator, sender=Shirt)


class Rating(models.Model):
    id = models.IntegerField(primary_key=True, auto_created=True, editable=False)
    shirt = models.ForeignKey("Alt.Shirt", on_delete=models.CASCADE, null=True, blank=True)
    nonprofit = models.ForeignKey('Alt.NonProfit', null=True, blank=True,on_delete=models.CASCADE)
    project = models.ForeignKey('Alt.NonProfitProject', null= True, blank=True,on_delete=models.CASCADE)
    company = models.ForeignKey('Alt.ForProfitCompany', blank=True, null=True,on_delete=models.CASCADE)
    user = models.ForeignKey("api.UserProfile", on_delete=models.CASCADE)
    stars = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    # class Meta:
        # unique_together = [['user','shirt'],['user','company'], ['user','nonprofit'],['user','project']]
        # index_together = (['user', 'shirt'],['user','company'], ['user','nonprofit'],['user','project'])


    def __str__(self):
        if self.shirt:
            return self.shirt.name
        elif self.nonprofit:
            return self.nonprofit.name
        elif self.project:
            return self.project.title
        elif self.compay:
            return self.company.name

    def get_absolute_url(self):
        return reverse("Rating_detail", kwargs={"pk": self.pk})


class NonProfit(models.Model):
    name= models.CharField(max_length=50, blank=False, null=False)
    logo =  models.TextField(blank = True, null = True)
    video = models.TextField(blank = True, null=True)
    description =models.TextField(blank=True, null=True)
    year_started = models.IntegerField(blank = True, null= True)
    mission_statement=models.TextField(blank=True, null=True)
    vision_statement=models.TextField(blank=True, null=True)
    website_url= models.URLField(blank=True, null=True)
    city= models.CharField(max_length=60, blank=True, null= True )
    category = models.ManyToManyField(Category, blank=True, related_name='NonProfit' )
    slug = models.SlugField(unique = True, blank =True, null= True)
    featured = models.BooleanField(blank=False, null=False, default=False)
    date_added= models.DateTimeField(auto_now_add=True)
    main_image= models.CharField(max_length=200, blank= True, null = True)
    owner = models.OneToOneField('api.UserProfile', on_delete=models.CASCADE, related_name='nonprofit', null=True)
    contributors = models.ManyToManyField('api.UserProfile', related_name='contributors', blank= True)
    facebook = models.CharField(max_length = 30, blank = True, null = True)
    instagram = models.CharField(max_length = 30, blank = True, null = True)

    @property
    def companies_supporting(self):
        companies= self.company.all()
        company_list=[]
        for company in companies:
            if(company.logo):
                company_list.append({company.name: company.logo})
            company_list.append({company.name})
        return company_list


    @property
    def nonprofit_links(self):
        links = 'api.Links'.objects.filter(nonprofit = self)
        return links

    @property
    def total_balance(self):
        return self.balance.balance

    @property
    def shirtList(self):
        categories = self.category.all()
        for category in categories:
            return category.shirt.all()
    @property
    def atrocity_List(self):
        categories = self.category.all()
        for category in categories:
            return category.atrocity.all()

    @property
    def no_of_ratings(self):
        ratings = Rating.objects.filter(nonprofit =self)
        return len(ratings)

    @property
    def average_rating(self):
        sum = 0
        ratings = Rating.objects.filter(nonprofit =self)
        for rating in ratings:
            sum += rating.stars
        if len(ratings) > 0:
            return sum /len(ratings)
        else:
            return 0

    def get_absolute_url(self):
        return reverse("Alt:NonProfit", kwargs={"slug": self.slug})


    def get_categories(self):
        return NonProfit.objects.filter(category__id =self.id)

    def __str__(self):
        return self.name

    def slugFormatter(self):
        word = self.name
        update = word.split()[0]
        return update

    def save(self, *args, **kwargs):
        if self.slug is None:
            slug = self.slugFormatter()
            year = str(self.year_started)
            self.slug = slug + year
            super(NonProfit, self).save()
        super(NonProfit,self).save()


class OrderItem(models.Model):
    user = models.ForeignKey("api.UserProfile", on_delete=models.CASCADE)
    ordered_shirt = models.ForeignKey("Alt.Shirt", on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    color = models.ForeignKey("Alt.ShirtColor", on_delete=models.CASCADE, related_name='item', blank = True, null = True)
    size =  models.ForeignKey('Alt.ShirtSize',  on_delete=models.CASCADE, blank = True, null = True )
    ordered = models.BooleanField(default=False)
    printful_variant_id= models.CharField(blank= True, null=True, max_length=100)
    mockup_task_key= models.CharField(blank=True, null=True, max_length=100)
    mockup_generation_complete = models.BooleanField(default = False)

    def __str__(self):
        return '{} of {}'.format(self.quantity, self.ordered_shirt.name)


    def get_total_shirt_price(self):
        return self.quantity * self.ordered_shirt.price

    def get_discount_shirt_price(self):
        return self.quantity * self.ordered_shirt.discount_price

    def get_amount_donated(self):
        return self.get_total_shirt_price() * .35

    def get_final_price(self):
        if self.ordered_shirt.discount_price:
            return self.get_discount_shirt_price()
        return self.get_total_shirt_price()


class Payment(models.Model):
    card_holder_name = models.CharField(max_length=100)
    card_number = models.CharField(max_length=16)  # Store the last 4 digits for reference
    expiry_date = models.CharField(max_length=10)
    cvv = models.CharField(max_length=4)
    address = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.card_holder_name+''+ str(self.amount)


class Order(models.Model):
    PAYMENT_TYPE =(
        (1, 'Card'),
        (2, 'AltruePoints'),
        (3, 'Hybrid'),

    )
    STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('in_production', 'In Production'),
    ('shipped', 'Shipped'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    user = models.ForeignKey("api.UserProfile", on_delete=models.CASCADE, related_name='orders')
    shirts = models.ManyToManyField("Alt.OrderItem", blank =True)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField(auto_now_add=True)
    points_paid = models.IntegerField(null=True, blank=True)
    amount_paid  = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    completed = models.BooleanField(default = False)
    stripe_id = models.CharField(max_length=50)
    paid_for = models.BooleanField(default=False)
    payment_type = models.IntegerField(choices=PAYMENT_TYPE, null=True, blank=True)
    mockups_for_order = ManyToManyField('Alt.Mockup',  blank=True)
    printful_fullfillment_started = models.BooleanField(default=False)
    fullfillment_id = models.CharField(blank=True, null =True, max_length=30)
    backend_fullfillment_started = models.BooleanField(default=False)
    tracking_number = models.CharField(max_length=50, blank=True, null=True)
    carrier = models.CharField(max_length=50, blank=True, null=True)
    tracking_url = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.user.email

    def get_total_price(self):
        total = 0
        for order_item in self.shirts.all():
            total += order_item.get_final_price()
        return total


class Mockup(models.Model):
    order_item = models.ForeignKey(OrderItem, null=False, blank=False, on_delete=models.CASCADE)
    url= models.CharField(max_length= 150, blank=False, null= False)
    verified = models.BooleanField(default=False)
    created=models.DateTimeField(auto_now_add=True, blank=True, null=True)


class Cart(models.Model):
    user = models.ForeignKey('api.UserProfile', on_delete=models.CASCADE)
    items = models.ManyToManyField("Alt.OrderItem" )


class CheckoutAddress(models.Model):
    user = models.ForeignKey('api.UserProfile', on_delete=models.CASCADE)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100, blank=True, null=True)
    country = CountryField(multiple=False)
    zip = models.CharField(max_length=100)
    special_directions = models.TextField(blank= True, null = True)

    def __str__(self):
        return self.user.email


class NonProfitBalance(models.Model):
    nonprofit= models.OneToOneField(NonProfit, on_delete=models.CASCADE, related_name='balance')
    balance = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    updated_at = models.DateField(auto_now=True)
    
    def __str__(self):
        return self.nonprofit.name
    def get_absolute_url(self):
        return reverse("NonProfitBalOreance_detail", kwargs={"pk": self.pk})

class AtrocityBalance(models.Model):
    atrocity = models.OneToOneField(Atrocity, on_delete=models.CASCADE, related_name = 'balance')
    balance = models.DecimalField(decimal_places=2, max_digits = 10, default=0)
    last_transaction = models.DateTimeField( auto_now=True, null= True, blank= True)

    def __str__(self):
        return self.atrocity.title

    def get_absolute_url(self):
        return reverse('AtrocityBalance_detail', kwargs={"pk": self.pk})


class CompanyStore(models.Model):
    street_address = models.CharField(max_length=10, blank= True, null=True)
    zip = models.CharField(max_length=100, blank = True, null=True)
    country = CountryField(multiple=False)
    state = models.CharField(max_length=2, null=True, blank=True)




    class Meta:
        verbose_name = ("CompanyStore")
        verbose_name_plural = ("CompanyStores")

    def __str__(self):
        return self.location

    def get_absolute_url(self):
        return reverse("CompanyStore_detail", kwargs={"pk": self.pk})


class ForProfitCompany(models.Model):
    owner = models.OneToOneField("api.UserProfile", on_delete=models.CASCADE)
    name= models.CharField(max_length = 30, blank=False, null= False)
    contributors = ManyToManyField("api.UserProfile",related_name='forprofitcontributors', blank=True)
    nonprofits = ManyToManyField(NonProfit,related_name='company_nonprofit', blank= True)
    atrocities = ManyToManyField(Atrocity, related_name ='company_atrocity', blank = True)
    year_started = models.CharField(max_length= 4, blank = False, null=False)
    logo = models.CharField(max_length = 200, blank=True, null=True, default='https://i.ibb.co/yPCqbSG/altruecompany-placeholder.png')
    image = models.CharField(max_length = 200, blank=True, null=True)
    headquarters = models.CharField(max_length = 50,  blank= True, null= True)
    mission = models.CharField(max_length = 100, blank=True, null= True)
    locations = ManyToManyField(CompanyStore, related_name = 'company', blank=True)
    description = models.TextField(blank= False, null = False)
    website_address = models.TextField(blank=True, null = True)
    slug = models.SlugField(blank=True, null=True, unique=True)
    categories = models.ManyToManyField(Category, related_name = 'company', blank = True)
    contributors_pending = models.ManyToManyField('api.UserProfile', related_name='contributors_pending', blank =True)
    is_featured= models.BooleanField(default= False)
    facebook = models.CharField(max_length = 50, blank= True, null =True)
    instagram = models.CharField(max_length =30,blank = True, null =True)
    coupons_of_company = ManyToManyField('Alt.CompanyCoupon', related_name='coupons_of_company', blank=True)


    class Meta:
        verbose_name_plural = ("ForProfitCompanies")

    def __str__(self):
        return self.name

    # def get_absolute_url(self):
    #     return reverse("CompanyStore_detail", kwargs={"pk": self.pk})

    def slugFormatter(self):
        word = self.name
        update = word.split()[0]
        return update

    def save(self, *args, **kwargs):
        slug = self.slugFormatter()
        self.slug = slug + self.year_started
        super(ForProfitCompany, self).save()


class CompanyCoupon(models.Model):
    name= models.CharField(max_length = 30, blank=False, null=False)
    locations =models.ManyToManyField('Alt.CompanyStore', related_name ='coupon', blank=True, )
    company = models.ForeignKey('Alt.ForProfitCompany',  on_delete=models.CASCADE, related_name='coupon', blank =False, null=False)
    coupon_code = models.CharField(max_length= 12, blank = True, null = True)
    expiration_date = models.DateField(blank = True, null=True)
    description =  models.TextField(blank= True, null=True)
    coupon_image = models.CharField(blank = True, null=True, max_length=200)
    slug = models.SlugField(blank=True, null=True )




    class Meta:
        verbose_name = ("CompanyCoupon")
        verbose_name_plural = ("CompanyCoupons")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("CompanyCoupon_detail", kwargs={"pk": self.pk})


    def save(self, *args, **kwargs):
        self.slug = self.company.name + str(self.pk)
        self.coupon_code = random.randint(100000000000,999999999999)

        if not self.name:
            self.name = self.slug
        super(CompanyCoupon, self).save()


class UserMatchRelationShip(models.Model):

    MATCH_PERCENTAGE =(
        (5, 'Five Percent'),
        (10, 'Ten Percent'),
        (25, 'Twenty Five Percent'),
        (50, 'Fifty Percent'),
        (100, 'Full Match')
    )
    user_matching_donation = models.ForeignKey('api.UserProfile',related_name='user_matching', on_delete=models.CASCADE)
    user_being_matched = models.ForeignKey('api.UserProfile', related_name='user_being_matched', on_delete=models.CASCADE)
    funding_limit =models.FloatField(default=0, null = True, blank=True)
    needs_permission = models.BooleanField(default=True, blank = True)
    match_level = models.IntegerField(choices=MATCH_PERCENTAGE)
    was_confirmed = models.BooleanField(default= False, blank = False )

    class Meta:

        def __str__(self):
            return '{} matches {} for donations to {}'.format(self.user_matching_donation, self.match_level, self.user_being_matched)


class NonProfitDonation(models.Model):
    nonprofit= models.ForeignKey(NonProfit, related_name='nonprofitdonation', on_delete=models.CASCADE)
    donation_date = models.DateTimeField( auto_now_add=True, null=False, blank=False)
    donation_amount = models.DecimalField(max_digits=9, decimal_places=2)
    profile_donated = models.ForeignKey('api.UserProfile', related_name='profile_donating', on_delete=models.CASCADE)
    
    class Meta:
        def __str__(self):
            return '{} donation from {}'.format(self.nonprofit.name, self.profile_donated.username)


class AtrocityDonation(models.Model):
    atrocity= models.ForeignKey(Atrocity, related_name='atrocitydonation', on_delete=models.CASCADE)
    donation_date = models.DateTimeField( auto_now_add=True, null=False, blank=False)
    donation_amount = models.DecimalField(max_digits=9, decimal_places=2)
    profile_donated = models.ForeignKey('api.UserProfile', related_name='profile', on_delete=models.CASCADE)
    
    class Meta:
        def __str__(self):
            return '{} donation from {}'.format(self.atrocity.title, self.profile_donated.username)

class NonProfitProjectDonation(models.Model):
    nonprofit= models.ForeignKey(NonProfit, related_name='projectdonation', on_delete=models.CASCADE)
    donation_date = models.DateTimeField( auto_now_add=True, null=False, blank=False)
    donation_amount = models.DecimalField(max_digits=9, decimal_places=2)
    profile_donated = models.ForeignKey('api.UserProfile', related_name='donations_made', on_delete=models.CASCADE)
    project = models.ForeignKey('Alt.NonProfitProject', related_name='nonprofitproject', on_delete=models.CASCADE)
    
    class Meta:
        def __str__(self):
            return '{} donation from {} for {}'.format(self.nonprofit.name, self.profile_donated.username, self.project.title)


class UserMatchTransaction(models.Model):
    relationship = models.ForeignKey('Alt.UserMatchRelationShip', related_name='user_match_transaction', on_delete=models.CASCADE)
    transaction_date = models.DateTimeField( auto_now_add=True, null=False, blank=False)
    total_amount = models.FloatField(blank=True, null=True)
    confirmed = models.BooleanField(default = False)


    class Meta:
        verbose_name =('UserMatchTransactions')


    def __str__(self):
        return self.relationship.user_being_matched.username


class CompanyNonProfitRelationship(models.Model):

    MATCH_PERCENTAGE =(
        (10, 'Ten Percent'),
        (25, 'Twenty Five Percent'),
        (50, 'Fifty Percent'),
        (100, 'Full Match')
    )
    company = models.ForeignKey('Alt.ForProfitCompany',  on_delete=models.CASCADE, related_name='npcompanyrelation')
    nonprofit = models.ForeignKey("Alt.NonProfit",  on_delete=models.CASCADE, related_name='npcompanyrelation')
    match_level = models.IntegerField(choices=MATCH_PERCENTAGE)
    total_raised = models.FloatField(default=0, null=True, blank= True)
    funding_limit = models.FloatField(default=0, null=True, blank=True )
    completed = models.BooleanField(default= False, blank = True)




    class Meta:
        verbose_name = ("CompanyNonProfitRelationship")
        verbose_name_plural =("CompanyNonProfitRelationships")

    def __str__(self):
        return '{} matches {}%% for donations to {}'.format(self.company.name, self.match_level, self.nonprofit.name)

    def get_absolute_url(self):
        return reverse("CompanyNonProfitRelationship_detail", kwargs={"pk": self.pk})


class CompanyAtrocityRelationship(models.Model):

    MATCH_PERCENTAGE =(
        (10, 'Ten Percent'),
        (25, 'Twenty Five Percent'),
        (50, 'Fifty Percent'),
        (100, 'Full Match')
    )
    company = models.ForeignKey('Alt.ForProfitCompany',  on_delete=models.CASCADE, related_name='atrocitycompanyrelation')
    atrocity = models.ForeignKey('Alt.Atrocity',  on_delete=models.CASCADE, related_name='atrocitycompanyrelation')
    match_level = models.IntegerField(choices=MATCH_PERCENTAGE)
    total_raised = models.FloatField(default = 0, blank= True, null= True)
    funding_limit = models.FloatField(blank=True, null=True, default=0)
    completed = models.BooleanField(default = False, blank =True)


    class Meta:
        verbose_name = ("CompanyAtrocityRelationship")
        verbose_name_plural = ("CompanyAtrocityRelationships")

    def __str__(self):
        return '{} matches {}"%" for donations to {}'.format(self.company.name, self.match_level, self.atrocity.title)

    def get_absolute_url(self):
        return reverse("CompanyAtrocityRelationship_detail", kwargs={"pk": self.pk})

class CompanyProjectRelationShip(models.Model):
    MATCH_PERCENTAGE =(
        (10, 'Ten Percent'),
        (25, 'Twenty Five Percent'),
        (50, 'Fifty Percent'),
        (100, 'Full Match')
    )
    company = models.ForeignKey('Alt.ForProfitCompany', related_name='project_match_company', on_delete=models.CASCADE)
    project =  models.ForeignKey('Alt.NonProfitProject', related_name='project_match', on_delete=models.CASCADE)
    match_level = models.IntegerField(choices=MATCH_PERCENTAGE)
    total_raised = models.FloatField(default = 0, blank= True, null= True)
    funding_limit = models.FloatField(blank=True, null=True, default=0)
    completed = models.BooleanField(default = False, blank=True)

    def __str__(self):
        return '{} matches {}"%" for donations to {}'.format(self.company.name, self.match_level, self.project.title)


class CompanyBalance(models.Model):
    company = models.OneToOneField("Alt.ForProfitCompany",  on_delete=models.CASCADE)
    balance = models.DecimalField( max_digits=7, decimal_places=2, default =0)
    last_transaction = models.DateTimeField(auto_now= True, null=True, blank = True)

    def __str__(self):
        return self.company.name


class CompanyDonation(models.Model):
    company = models.ForeignKey('Alt.ForProfitCompany', on_delete=models.CASCADE, related_name='company_donation')
    wallet = models.ForeignKey('Alt.CompanyBalance', on_delete=models.CASCADE, related_name = 'company_donation')
    amount = models.DecimalField( max_digits=6, decimal_places=2)
    nonprofit = models.ForeignKey('Alt.NonProfit', blank= True, null = True, on_delete=models.CASCADE, related_name = 'company_donation_nonprofit')
    atrocity = models.ForeignKey('Alt.Atrocity', blank=True, null=True, on_delete=models.CASCADE, related_name='company_donation_atrocity')
    project = models.ForeignKey('Alt.NonProfitProject', blank =True, null= True, on_delete = models.CASCADE, related_name= 'company_donation')
    donation_date = models.DateTimeField( auto_now_add=True, null=False, blank=False)

    def __str__(self):
        if self.nonprofit:
            return '{} donates {} to {}'.format(self.company.name, self.amount, self.nonprofit.name)
        elif self.atrocity:
            return '{} donates {} to {}'.format(self.company.name, self.amount, self.atrocity.title)
        elif self.project:
            return '{} donates to {} to {}'.format(self.company.name, self.amount, self.project.title)


class NonProfitProject(models.Model):
    nonprofit = models.ForeignKey('Alt.NonProfit', on_delete=models.CASCADE, related_name='np_project_nonprofit', blank=True, null=True)
    cause = models.ForeignKey('Alt.Category', on_delete=models.CASCADE, related_name='np_project_cause', blank = True, null=True)
    atrocity = models.ForeignKey('Alt.Atrocity', on_delete=models.CASCADE, related_name='np_project_atrocity', blank= True, null= True)
    title = models.CharField(max_length = 140, blank = True, null = True)
    information = models.TextField(blank = True, null = True)
    fundraising_goal = models.IntegerField()
    total_raised = models.DecimalField(decimal_places=2, max_digits=9, default=0)
    followers = models.ManyToManyField('api.UserProfile', related_name='np_project_followers' , blank = True)
    supporters = models.ManyToManyField('api.UserProfile', related_name='np_project_supporters', blank = True)
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default= False)
    project_image = models.CharField( blank = True,null = True,max_length=200)
    supplies = models.TextField(blank =True, null = True)
    project_image_file= models.ImageField(upload_to='project_images/', blank=True, null=True)


    def __str__(self):
        if self.title:
            return '{} : {}'.format(self.nonprofit.name, self.title)
        return self.nonprofit.name


    def get_absolute_url(self):
        return reverse("NonProfitProject_detail", kwargs={"pk": self.pk})

    def makeInactive(self):
        if self.is_active == True and self.total_raised >= self.fundraising_goal:
            self.is_active = False
        pass

    def no_of_ratings(self):
        ratings = Rating.objects.filter(project =self)
        return len(ratings)

    def average_rating(self):
        sum = 0
        ratings = Rating.objects.filter(project =self)
        for rating in ratings:
            sum += rating.stars
        if len(ratings) > 0:
            return sum /len(ratings)
        else:
            return 0

    def save(self, *args, **kwargs):
        self.makeInactive()
        super(NonProfitProject, self).save()


class NonProfitAtrocityRelationShip(models.Model):
    nonprofit = models.ForeignKey('Alt.NonProfit', on_delete=models.CASCADE, related_name='nonprofitatrocityRelationship')
    atrocity = models.ForeignKey('Alt.Atrocity', on_delete= models.CASCADE, related_name='nonprofitAtrocityRelationship')
    projects = models.ManyToManyField('Alt.NonProfitProject', related_name='nonprofitAtrocityRelationship', blank= True)


    def __str__(self):
        if self.projects:
            return '{} is working on {} project to help {}'.format(self.nonprofit.name, len(self.projects.all()), self.atrocity)
        return  '{} is working to help {}'.format(self.nonprofit.name, self.atrocity.title)

    def get_absolute_url(self):
        return reverse("NonProfitAtrocityRelationship_detail", kwargs={"pk": self.pk})

class QuizAnswers(models.Model):
    answer = models.CharField(max_length=100)
    isCorrect = models.BooleanField()

    def __str__(self):
        return self.answer


class QuizQuestion(models.Model):
    question_text= models.TextField(blank= False, null= False)
    choices = models.ManyToManyField(QuizAnswers,)
    isLocked = models.BooleanField(default=False)
    selectedOption = models.ForeignKey(QuizAnswers, related_name='selected', on_delete=models.CASCADE, blank=True, null=True)
    def __str__(self):
        return self.question_text


class Quiz(models.Model):
    title = models.TextField(blank = False, null=False)
    description = models.TextField(blank = True, null = True)
    atrocity = models.ForeignKey('Alt.Atrocity', on_delete=models.CASCADE, null=True, blank= True)
    question = models.ManyToManyField(QuizQuestion)
    action =models.ForeignKey(AltrueAction,  on_delete=models.CASCADE, blank=True, null= True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, blank = True, null= True)

    def __str__(self):
        return self.title
    

class QuizResult(models.Model):
    user = models.ForeignKey("api.UserProfile",  on_delete=models.CASCADE)
    quiz = models.ForeignKey('Alt.Quiz', on_delete=models.CASCADE )
    num_correct = models.IntegerField()
    score = models.DecimalField(max_digits=5, decimal_places=2)
    completion_time = models.DateTimeField(auto_now_add=True)


class ShareRecord(models.Model):
    user = models.ForeignKey("api.UserProfile",  on_delete=models.CASCADE)
    atrocity = models.ForeignKey(Atrocity, blank=True, null=True, on_delete=models.CASCADE)
    nonprofit = models.ForeignKey(NonProfit, blank=True, null=True,on_delete=models.CASCADE )
    project = models.ForeignKey(NonProfitProject, blank=True, null=True, on_delete=models.CASCADE)
    completion_time = models.DateTimeField(auto_now_add=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE,blank =True, null=True)


# Model Signals Below ---->>>


@receiver(email_confirmed)
def send_welcome_email(request, email_address, **kwargs):
    user = email_address.user
    current_site = Site.objects.get_current()  # Assuming you correctly retrieve the current site
   
    # Prepare context for the email template
    context = {
        "user": user,
        "current_site": current_site,
    }

    # Load the email template
    html_template = get_template("account/welcome_email.html")
    html_content = html_template.render(context)

    # Send the email using EmailMultiAlternatives
    subject = "Welcome to Altrue"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = email_address.email

    msg = EmailMultiAlternatives(subject, html_content, from_email, [to_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()





@receiver(post_save, sender= NonProfit)
def create_nonprofit_account(sender, instance=None, created=False, **kwargs ):
    if created:
        NonProfitBalance.objects.create(nonprofit =instance)
    else:
        non = NonProfitBalance.objects.filter(nonprofit = instance)
        if non.exists():
            pass
        else:
            NonProfitBalance.objects.create(nonprofit= instance)


@receiver(post_save, sender = ForProfitCompany)
def create_company_wallet(sender, instance = None, created=False, **kwargs):
    if created:
        CompanyBalance.objects.create(company =instance)
    else:
        comp = CompanyBalance.objects.filter(company =instance)
        if comp.exists():
            pass
        else:
            CompanyBalance.objects.create(company = instance)

@receiver(post_save, sender = Atrocity)
def create_atrocity_account(sender, instance=None, created=False, **kwargs):
    if created:
        AtrocityBalance.objects.create(atrocity = instance)
    else:
        atro = AtrocityBalance.objects.filter(atrocity = instance)
        if atro.exists():
            pass
        else:
            AtrocityBalance.objects.create(atrocity = instance)


@receiver(post_save, sender=NonProfitDonation)
def updateNPBalanceAfterReceivingDonation(instance,**kwargs ):
    with transaction.atomic():
        nonprofitBalance = NonProfitBalance.objects.get(nonprofit = instance.nonprofit)
        nonprofitBalance.balance += instance.donation_amount
        nonprofitBalance.save()


@receiver(post_save, sender=NonProfitProjectDonation)
def updateNPBalanceAfterProjectDonation(instance,**kwargs ):
    with transaction.atomic():
        nonprofitBalance = NonProfitBalance.objects.get(nonprofit = instance.nonprofit)
        nonprofitBalance.balance += instance.donation_amount
        nonprofitBalance.save()


@receiver(post_save, sender=NonProfitProjectDonation)
def updateAtrocityBalanceAfterDonation(instance, **kwargs):
    with transaction.atomic():
        atrocityBalance = AtrocityBalance.objects.get(atrocity = instance.atrocity)
        atrocityBalance.balance += instance.donation_amount
        atrocityBalance.save()

# @receiver([post_save, post_delete], sender= 'api.UserDonation')
# def updateBalancesFromUserDonation( instance, **kwargs):

#     if instance.project:
#         project = NonProfitProject.objects.get(pk = instance.project.pk)
#         project.supporters.add(instance.user)
#         project.save()
#     if instance.nonprofit:
#         nonprof= NonProfitBalance.objects.get(nonprofit = instance.nonprofit)
#         if instance.amount > 0:
#             new_amount = instance.dollar_amount + nonprof.balance
#             nonprof.balance = new_amount
#             nonprof.save(update_fields =['balance'])
#         else: pass
#     elif instance.atrocity:
#         atroc = AtrocityBalance.objects.get(atrocity = instance.atrocity)
#         if instance.amount > 0:
#             new_amount = instance.amount + atroc.balance
#             atroc.balance = new_amount
#             atroc.save(update_fields =['balance'])
#         else:pass
#     else:
#         pass

@receiver(post_save, sender = NonProfitProject)
def createNPRelationShipIfnotCreated(instance, created, **kwargs):
    if created and instance.atrocity:
       obj,created = NonProfitAtrocityRelationShip.objects.get_or_create(atrocity = instance.atrocity, nonprofit =instance.nonprofit)
       obj.projects.add(instance)


@receiver(post_save, sender=Order,dispatch_uid ='initiate_order_fullfillment')
def initiate_order_fulfillment(instance,created, sender, **kwargs):
        if instance.paid_for and not instance.completed and not instance.backend_fullfillment_started:
            instance.backend_fullfillment_started = True
            print('fulfillment started', instance.id)
            for order_item in instance.shirts.all():
                print(order_item)
                find_variant(order_item)
                generate_mockups_for_order(instance)


# @receiver(post_save, sender= 'api.UserProfile')
# def friendInvite(instance, created, **kwargs):
#     if created:
#         FriendInvite.objects.get(inviter = str(instance.user.email))


# @receiver(post_save, sender = 'api.UserProfile')
# def created


@receiver(post_save, sender ='api.CompanyMatchDonation')
def updateTotals(instance, created = True, **kwargs):
    if created:

        if instance.project!= None:
            co = ForProfitCompany.objects.get(pk =instance.company_id)
            wallet = CompanyBalance.objects.get(company =co)
            amount = float(instance.amount)
            new_company_wallet_amount = float(wallet.balance) - amount
            wallet.balance = new_company_wallet_amount
            wallet.save(update_fields=['balance'])

            try:
                com = CompanyNonProfitRelationship.objects.get(company = instance.company, nonprofit =instance.nonprofit)
                np = com.np
                np_balance = NonProfitBalance.objects.get(nonprofit = np)
                np_balance.balance = np_balance.balance + amount
                np_balance.save()
                updated_total = float(instance.amount) + com.total_raised
                com.total_raised = updated_total
                com.save(update_fields=['total_raised'])


                proRelationShip = CompanyProjectRelationShip.objects.get(company=instance.coompany, project = instance.project)
                proRelationShip.total_raised = proRelationShip.total_raised + instance.amount
                proRelationShip.save()




            except: ObjectDoesNotExist

        if instance.nonprofit != None:
            co = ForProfitCompany.objects.get(pk =instance.company_id)
            wallet = CompanyBalance.objects.get(company =co)

            # CompanyDonation.objects.create(amount= instance.amount, nonprofit = instance.nonprofit, company = instance.company, wallet = wallet)
            amount = float(instance.amount)
            new_company_wallet_amount = float(wallet.balance) - amount
            wallet.balance = new_company_wallet_amount
            wallet.save(update_fields=['balance'])

            try:
                com = CompanyNonProfitRelationship.objects.get(company = instance.company, nonprofit =instance.nonprofit)
                nonprof = com.nonprofit
                balance = NonProfitBalance.objects.get(nonprofit = nonprof)
                balance.balance = float(balance.balance) + amount
                balance.save()
                updated_total = float(instance.amount) + com.total_raised
                com.total_raised = updated_total
                com.save(update_fields=['total_raised'])

            except: ObjectDoesNotExist
        elif instance.atrocity != None:
            cos = ForProfitCompany.objects.get(pk =instance.company_id)
            wallet = CompanyBalance.objects.get(company=cos)
            # CompanyDonation.objects.create(amount= instance.amount, nonprofit = instance.nonprofit, company = instance.company, wallet = wallet)
            amount = float(instance.amount)
            new_company_wallet_amount = float(wallet.balance) - amount
            wallet.balance = new_company_wallet_amount
            wallet.save(update_fields=['balance'])
            try:
                co = CompanyAtrocityRelationship.objects.get(company = instance.company, atrocity = instance.atrocity)
                atroc = co.atrocity
                balance = AtrocityBalance.objects.get(atrocity = atroc)
                balance.balance = balance.balance + amount
                balance.save()
                updated_tot = float(instance.amount) + co.total_raised
                co.total_raised = updated_tot
                co.save(update_fields=['total_raised'])

            except: ObjectDoesNotExist
        pass
