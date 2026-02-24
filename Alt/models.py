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


# ============================================================================
# COMPANY ECOSYSTEM MODELS - Phase 1 Implementation
# ============================================================================
# These models support the company tiered ecosystem with escrow wallets,
# campaign management, and enhanced rewards system.
# ============================================================================

class CompanyTier(models.Model):
    """
    Tracks company subscription tier and billing configuration.
    Free: 3% transaction fee, Pro: $299/mo + 1%, Enterprise: $999/mo + 0.5%
    """
    TIER_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro ($299/mo)'),
        ('enterprise', 'Enterprise ($999/mo)'),
    ]
    
    company = models.OneToOneField(
        'Alt.ForProfitCompany', 
        on_delete=models.CASCADE,
        related_name='tier'
    )
    tier = models.CharField(
        max_length=20, 
        choices=TIER_CHOICES, 
        default='free'
    )
    monthly_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )
    transaction_fee_percent = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=3.00  # 3% for free tier
    )
    stripe_subscription_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True
    )
    stripe_customer_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Company Tier"
        verbose_name_plural = "Company Tiers"
    
    def __str__(self):
        return f"{self.company.name} - {self.get_tier_display()}"
    
    def save(self, *args, **kwargs):
        # Auto-set fees based on tier
        if self.tier == 'free':
            self.monthly_fee = 0.00
            self.transaction_fee_percent = 3.00
        elif self.tier == 'pro':
            self.monthly_fee = 299.00
            self.transaction_fee_percent = 1.00
        elif self.tier == 'enterprise':
            self.monthly_fee = 999.00
            self.transaction_fee_percent = 0.50
        super().save(*args, **kwargs)


class CompanyWallet(models.Model):
    """
    Escrow wallet for company matching funds.
    Companies pre-fund this wallet (30% of budget) before matches are made.
    This ensures Altrue has no upfront liability.
    """
    company = models.OneToOneField(
        'Alt.ForProfitCompany', 
        on_delete=models.CASCADE,
        related_name='matching_wallet'
    )
    # Available balance for matching
    balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00
    )
    # Monthly budget cap set by company
    monthly_budget = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00
    )
    # Amount matched this month
    matched_this_month = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00
    )
    # Auto-pause matching when balance below this threshold
    auto_pause_threshold = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=50.00
    )
    # Auto-refill settings
    auto_refill_enabled = models.BooleanField(default=False)
    auto_refill_threshold = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=100.00
    )
    auto_refill_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=500.00
    )
    # Status
    is_active = models.BooleanField(default=True)
    is_paused = models.BooleanField(default=False)
    paused_at = models.DateTimeField(null=True, blank=True)
    pause_reason = models.TextField(blank=True, null=True)
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Company Matching Wallet"
        verbose_name_plural = "Company Matching Wallets"
    
    def __str__(self):
        return f"{self.company.name} Wallet - ${self.balance}"
    
    @property
    def remaining_budget(self):
        """Calculate remaining budget for current month"""
        return self.monthly_budget - self.matched_this_month
    
    @property
    def can_match(self):
        """Check if company has sufficient funds for matching"""
        return (
            self.is_active and 
            not self.is_paused and 
            self.balance > self.auto_pause_threshold and
            self.remaining_budget > 0
        )
    
    def check_and_pause(self):
        """Auto-pause matching if balance below threshold"""
        if self.balance < self.auto_pause_threshold and not self.is_paused:
            self.is_paused = True
            self.paused_at = timezone.now()
            self.pause_reason = "Balance below auto-pause threshold"
            self.save()
            return True
        return False


class CompanyApplication(models.Model):
    """
    Application workflow for companies wanting to join Altrue.
    Includes vetting process with manual review.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    # Company Information
    company_name = models.CharField(max_length=255)
    ein = models.CharField(max_length=20)
    website = models.URLField()
    mission_statement = models.TextField()
    description = models.TextField()
    
    # Annual commitment (minimum $10,000)
    annual_matching_commitment = models.DecimalField(
        max_digits=12, 
        decimal_places=2
    )
    
    # Contact Information
    contact_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Address
    street_address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    country = CountryField(blank=True, null=True)
    
    # Supporting Documents
    logo_url = models.CharField(max_length=500, blank=True, null=True)
    
    # Application Status
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    
    # Review Information
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        'api.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    rejection_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # If approved, link to created company
    approved_company = models.OneToOneField(
        'Alt.ForProfitCompany',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='application'
    )
    
    # EIN verification
    ein_verified = models.BooleanField(default=False)
    ein_verification_data = models.JSONField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Company Application"
        verbose_name_plural = "Company Applications"
        ordering = ['-applied_at']
    
    def __str__(self):
        return f"{self.company_name} - {self.get_status_display()}"


class CompanyMatchCampaign(models.Model):
    """
    Time-limited matching campaigns with escrow funding.
    Companies pre-fund 30% of campaign budget before launch.
    """
    CAMPAIGN_STATUS = [
        ('draft', 'Draft'),
        ('pending_funding', 'Pending Funding'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    company = models.ForeignKey(
        'Alt.ForProfitCompany',
        on_delete=models.CASCADE,
        related_name='campaigns'
    )
    
    # Campaign Details
    name = models.CharField(max_length=255)
    description = models.TextField()
    slug = models.SlugField(unique=True, blank=True, null=True)
    
    # Match Configuration
    match_multiplier = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        default=1.0,
        help_text="1.0 = 100% match, 2.0 = 2x match, etc."
    )
    max_match_per_donation = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Maximum match amount per individual donation"
    )
    
    # Campaign Timing
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Budget & Escrow
    budget_cap = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Maximum total matching for this campaign"
    )
    required_escrow = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="30% pre-funding required (auto-calculated)"
    )
    escrow_funded = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00
    )
    amount_matched = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00
    )
    
    # Eligibility
    eligible_causes = models.ManyToManyField(
        'Alt.Category',
        blank=True,
        related_name='campaigns'
    )
    eligible_nonprofits = models.ManyToManyField(
        'Alt.NonProfit',
        blank=True,
        related_name='campaigns'
    )
    min_donation_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=CAMPAIGN_STATUS,
        default='draft'
    )
    
    # Shirt Sponsorship (optional)
    shirt_sponsorship_enabled = models.BooleanField(default=False)
    sponsor_logo_placement = models.CharField(
        max_length=50,
        choices=[
            ('sleeve', 'Sleeve'),
            ('back', 'Back'),
            ('front_small', 'Front Small'),
        ],
        default='sleeve',
        blank=True,
        null=True
    )
    sponsor_shirt = models.ForeignKey(
        'Alt.Shirt',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='campaign_sponsorships'
    )
    
    # Analytics
    total_donations_matched = models.IntegerField(default=0)
    unique_donors = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    launched_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Company Match Campaign"
        verbose_name_plural = "Company Match Campaigns"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Calculate required escrow (30% of budget)
        if self.budget_cap:
            self.required_escrow = self.budget_cap * Decimal('0.30')
        
        # Auto-generate slug if not set
        if not self.slug:
            from django.template.defaultfilters import slugify
            base_slug = slugify(f"{self.company.name}-{self.name}")
            self.slug = base_slug
        
        super().save(*args, **kwargs)
    
    @property
    def remaining_budget(self):
        return self.budget_cap - self.amount_matched
    
    @property
    def is_fully_funded(self):
        return self.escrow_funded >= self.required_escrow
    
    @property
    def escrow_remaining(self):
        """Remaining escrow after matches"""
        return self.escrow_funded - self.amount_matched
    
    def can_launch(self):
        """Check if campaign can be launched"""
        return (
            self.status == 'pending_funding' and
            self.is_fully_funded and
            self.start_date > timezone.now()
        )


class CampaignEscrowTransaction(models.Model):
    """
    Tracks all escrow funding and match transactions for campaigns.
    """
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('match', 'Match Deduction'),
        ('refund', 'Refund'),
        ('overage_charge', 'Overage Charge'),
    ]
    
    campaign = models.ForeignKey(
        CompanyMatchCampaign,
        on_delete=models.CASCADE,
        related_name='escrow_transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    
    # For match transactions, link to donation
    donation = models.ForeignKey(
        'api.UserDonation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaign_match'
    )
    
    # Stripe payment intent (for deposits/charges)
    stripe_payment_intent_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Campaign Escrow Transaction"
        verbose_name_plural = "Campaign Escrow Transactions"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.campaign.name} - {self.transaction_type}: ${self.amount}"


class CompanyInvoice(models.Model):
    """
    Monthly billing for company subscription and transaction fees.
    """
    INVOICE_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    company = models.ForeignKey(
        'Alt.ForProfitCompany',
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    
    # Billing Period
    month = models.DateField()
    
    # Amounts
    monthly_fee = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00
    )
    total_matched = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00
    )
    transaction_fee_percent = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=0.00
    )
    altrue_fee = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00
    )
    total_due = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=INVOICE_STATUS,
        default='pending'
    )
    
    # Stripe
    stripe_invoice_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Company Invoice"
        verbose_name_plural = "Company Invoices"
        ordering = ['-month']
        unique_together = ['company', 'month']
    
    def __str__(self):
        return f"{self.company.name} - {self.month.strftime('%B %Y')} - ${self.total_due}"
    
    def calculate_fees(self):
        """Calculate Altrue fees based on matched amount"""
        self.altrue_fee = (self.total_matched * self.transaction_fee_percent) / 100
        self.total_due = self.monthly_fee + self.altrue_fee
        self.save()


class CompanyReward(models.Model):
    """
    Enhanced reward system for company-sponsored perks.
    Rewards live in user's Altrue Wallet for full analytics tracking.
    """
    REWARD_TYPES = [
        ('digital', 'Digital (Coupon/Code)'),
        ('physical', 'Physical Product'),
        ('experience', 'Experience/Event'),
    ]
    
    REWARD_STATUS = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
        ('depleted', 'Depleted'),
    ]
    
    company = models.ForeignKey(
        'Alt.ForProfitCompany',
        on_delete=models.CASCADE,
        related_name='rewards'
    )
    
    # Basic Info
    name = models.CharField(max_length=255)
    description = models.TextField()
    reward_type = models.CharField(
        max_length=20,
        choices=REWARD_TYPES
    )
    image_url = models.CharField(max_length=500, blank=True, null=True)
    
    # Unlock Criteria (can combine multiple)
    min_donation_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum donation to unlock this reward"
    )
    min_altrue_level = models.IntegerField(
        blank=True,
        null=True,
        help_text="Minimum Altrue level required"
    )
    min_streak_days = models.IntegerField(
        blank=True,
        null=True,
        help_text="Minimum donation streak days"
    )
    specific_cause = models.ForeignKey(
        'Alt.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rewards'
    )
    specific_nonprofit = models.ForeignKey(
        'Alt.NonProfit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rewards'
    )
    
    # Campaign-specific reward (optional)
    campaign = models.ForeignKey(
        CompanyMatchCampaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rewards'
    )
    
    # Fulfillment
    total_quantity = models.IntegerField(
        help_text="Total available rewards (0 = unlimited)"
    )
    claimed_count = models.IntegerField(default=0)
    
    # For physical rewards
    shipping_required = models.BooleanField(default=False)
    estimated_delivery_days = models.IntegerField(blank=True, null=True)
    
    # For digital rewards
    code_prefix = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Prefix for auto-generated codes (e.g., 'NIKE25')"
    )
    
    # Availability
    start_date = models.DateTimeField(null=True, blank=True)
    expiration_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=REWARD_STATUS,
        default='draft'
    )
    
    # Analytics
    views_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Company Reward"
        verbose_name_plural = "Company Rewards"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company.name} - {self.name}"
    
    @property
    def remaining_quantity(self):
        if self.total_quantity == 0:  # Unlimited
            return -1
        return self.total_quantity - self.claimed_count
    
    @property
    def is_available(self):
        now = timezone.now()
        return (
            self.status == 'active' and
            (self.start_date is None or self.start_date <= now) and
            (self.expiration_date is None or self.expiration_date > now) and
            (self.total_quantity == 0 or self.remaining_quantity > 0)
        )


class CompanyRewardCode(models.Model):
    """
    Individual coupon codes for digital rewards.
    Bulk uploaded or auto-generated.
    """
    reward = models.ForeignKey(
        CompanyReward,
        on_delete=models.CASCADE,
        related_name='codes'
    )
    code = models.CharField(max_length=255)
    
    # Claim tracking
    is_claimed = models.BooleanField(default=False)
    claimed_by = models.ForeignKey(
        'api.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claimed_reward_codes'
    )
    claimed_at = models.DateTimeField(null=True, blank=True)
    
    # Expiration (optional - can differ from reward expiration)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Redemption tracking
    is_redeemed = models.BooleanField(default=False)
    redeemed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Company Reward Code"
        verbose_name_plural = "Company Reward Codes"
        unique_together = ['reward', 'code']
    
    def __str__(self):
        return f"{self.reward.name} - {self.code[:10]}..."


class UserRewardClaim(models.Model):
    """
    Tracks user's rewards through the full lifecycle:
    unlocked -> viewed -> claimed -> redeemed
    """
    REWARD_STATUS = [
        ('unlocked', 'Unlocked'),
        ('viewed', 'Viewed'),
        ('claimed', 'Claimed'),
        ('fulfilled', 'Fulfilled'),
        ('redeemed', 'Redeemed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(
        'api.UserProfile',
        on_delete=models.CASCADE,
        related_name='reward_claims'
    )
    reward = models.ForeignKey(
        CompanyReward,
        on_delete=models.CASCADE,
        related_name='user_claims'
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=REWARD_STATUS,
        default='unlocked'
    )
    
    # For digital rewards
    reward_code = models.ForeignKey(
        CompanyRewardCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claims'
    )
    
    # For physical rewards - shipping
    shipping_address = models.TextField(blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Unlock trigger
    unlocked_by_donation = models.ForeignKey(
        'api.UserDonation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unlocked_rewards'
    )
    
    # Analytics timestamps
    unlocked_at = models.DateTimeField(auto_now_add=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    redeemed_at = models.DateTimeField(null=True, blank=True)
    
    # Notifications
    notification_sent = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "User Reward Claim"
        verbose_name_plural = "User Reward Claims"
        ordering = ['-unlocked_at']
        unique_together = ['user', 'reward']  # One claim per user per reward
    
    def __str__(self):
        return f"{self.user.username} - {self.reward.name} - {self.status}"
    
    def mark_viewed(self):
        if self.status == 'unlocked':
            self.status = 'viewed'
            self.viewed_at = timezone.now()
            self.save()
    
    def mark_claimed(self, reward_code=None):
        if self.status in ['unlocked', 'viewed']:
            self.status = 'claimed'
            self.claimed_at = timezone.now()
            if reward_code:
                self.reward_code = reward_code
            self.save()
    
    def mark_redeemed(self):
        if self.status == 'claimed':
            self.status = 'redeemed'
            self.redeemed_at = timezone.now()
            self.save()
            if self.reward_code:
                self.reward_code.is_redeemed = True
                self.reward_code.redeemed_at = timezone.now()
                self.reward_code.save()


class WalletTransaction(models.Model):
    """
    Tracks all deposits/withdrawals from company matching wallets.
    """
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('match', 'Match Payment'),
        ('refund', 'Refund'),
        ('auto_refill', 'Auto Refill'),
        ('campaign_escrow', 'Campaign Escrow Transfer'),
    ]
    
    wallet = models.ForeignKey(
        CompanyWallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    
    # Stripe reference
    stripe_payment_intent_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True
    )
    
    # For match payments
    matched_donation = models.ForeignKey(
        'api.UserDonation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transaction'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Wallet Transaction"
        verbose_name_plural = "Wallet Transactions"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.wallet.company.name} - {self.transaction_type}: ${self.amount}"


# ============================================================================
# SIGNALS FOR COMPANY ECOSYSTEM
# ============================================================================

@receiver(post_save, sender=ForProfitCompany)
def create_company_ecosystem_models(sender, instance, created, **kwargs):
    """
    Create associated models when a company is created.
    """
    if created:
        # Create CompanyTier (default to free)
        CompanyTier.objects.get_or_create(
            company=instance,
            defaults={'tier': 'free'}
        )
        
        # Create CompanyWallet
        CompanyWallet.objects.get_or_create(
            company=instance,
            defaults={'monthly_budget': 0.00}
        )


@receiver(post_save, sender=CompanyApplication)
def handle_application_approval(sender, instance, **kwargs):
    """
    When application is approved, create the ForProfitCompany.
    """
    if instance.status == 'approved' and not instance.approved_company:
        # Create the company
        company = ForProfitCompany.objects.create(
            owner=None,  # Will need to be linked to a user account
            name=instance.company_name,
            mission=instance.mission_statement,
            description=instance.description,
            website_address=instance.website,
            year_started=str(timezone.now().year),
            logo=instance.logo_url or 'https://i.ibb.co/yPCqbSG/altruecompany-placeholder.png'
        )
        
        # Link application to company
        instance.approved_company = company
        instance.save(update_fields=['approved_company'])
