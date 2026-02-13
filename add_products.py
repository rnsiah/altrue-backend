import stripe
from django.conf import settings
from Alt.models import Shirt

# Use environment-based Stripe key
stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_products():
    # Retrieve all Shirt objects
    shirts = Shirt.objects.all()

    for shirt in shirts:
        # Create product on Stripe
        product = stripe.Product.create(
            name=shirt.name,  # Use shirt name as product name
            description=shirt.shirt_style,  # Use shirt description as product description
            images=[shirt.shirt_image],  # Use shirt image as product image
            # Add other attributes as needed
        )

        # Create price object for the shirt
        price = stripe.Price.create(
            product=product.id,
            unit_amount=int(shirt.price * 100),  # Convert price to cents
            currency="usd",  # Use your preferred currency
            # Add other attributes as needed
        )

        # Assign product and price IDs from Stripe to the shirt object
        shirt.stripe_product_id = product.id
        shirt.stripe_price_id = price.id
        shirt.save()


# Call the function to create Stripe products and prices
create_stripe_products()
