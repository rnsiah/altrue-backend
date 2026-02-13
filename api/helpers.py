import requests
from django.conf import settings
import base64
import time

from django.contrib import admin


def find_variant(order_item):
    from Alt.models import ShirtSize
    print('running the find variant')
    # Define the endpoint URL
    endpoint = f"https://api.printful.com/products/{order_item.ordered_shirt.printful_id}"
    token= settings.PRINTFUL_API_TOKEN
    # Define the headers with the authorization token
    print(endpoint)
    print(token)
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Send the GET request to the API
        response = requests.get(endpoint, headers=headers)
        print(response)
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes

        # Parse the JSON response
        product_data = response.json()
        color= order_item.color.color
        size_id= order_item.size.size

        size= ShirtSize.objects.get(size=size_id).get_size_display()

        # Iterate through variants to find the matching one
        for variant in product_data["result"]["variants"]:
            if variant["color"] == color and variant["size"] == size:
                print(variant['id'])
                order_item.printful_variant_id=variant['id']
                order_item.save()

        # If the variant is not found
        return None

    except requests.exceptions.RequestException as e:
        # Handle any exceptions or errors
        print(f"Error finding variant: {e}")
        return None


# Function to create the mockup

# Function to save the mockup to the database


def generate_mockups_for_order(order):

          # URL of the sleeve image

        # Generate mockup for the current order item
        for order_item in order.shirts.all():
            print(f'about to generate the mockup for {order_item.ordered_shirt.name} ')
            if not order_item.mockup_generation_complete:
                print(f'generating for {order_item.pk}')
                generate_mockup(order_item)
                print('waiting to get the status')
                time.sleep(4)
                print('going to get the status')


            check_mockup_generation_status(order)

        # Handle the status


def generate_mockup(order_item):
    # Make API request to generate mockup
    print('generating mockups now')
    if not order_item.mockup_generation_complete:# Replace <YOUR_API_KEY> with your actual Printful API key
        qr = order_item.user.qrcode_url

        print(qr)

        url = f"https://api.printful.com/mockup-generator/create-task/{order_item.ordered_shirt.printful_id}"
        headers = {"Authorization": f"Bearer {settings.PRINTFUL_API_TOKEN}"}
        payload = {
            "variant_ids": [order_item.printful_variant_id],
            "format": "png",
            "product_options": {"lifelike": True},
            "files": [
                {
                    "placement": "front",
                    "image_url": order_item.ordered_shirt.shirt_image_front_file,
                    "position": {
                        "area_width": 1800,
                        "area_height": 2400,
                        "width": 1800,
                        "height": 1800,
                        "top": 250,
                        "left": 0,
                    },  # Adjust these values as needed
                },
                {
                    "placement": "sleeve_right",
                    "image_url": qr,
                    "position": {
                        "width": 600,
                        "height": 525,
                        "axrea_width": 300,
                        "area_height": 525,
                        "top": 0,
                        "left": 0,
                    },
                },
            ],
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            task_key = data["result"]["task_key"]
            order_item.mockup_task_key = task_key
            order_item.save()
            return True
        else:
            # Handle API request error
            print("Error:", response.text)
            return None
    else:
        print(f"Mockps already generated for order item {order_item.id}")
        return None


def check_mockup_generation_status(order):
    from Alt.models import Mockup
    # Make API request to check mockup generation status
    # Replace <YOUR_API_KEY> with your actual Printful API key
    for order_item in order.shirts.all():

        url = "https://api.printful.com/mockup-generator/task?task_key={}".format(order_item.mockup_task_key)
        headers = {"Authorization": f"Bearer {settings.PRINTFUL_API_TOKEN}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            status = data["result"]["status"]
            print({'theStatus':status})
            if status =='completed':
                order_item.mockup_generation_complete = True
                order_item.save()
                mockup_data = data['result']['mockups']
                print({'mockup_data':mockup_data})
                for mockup in mockup_data:
                    themockup=Mockup.objects.create(
                        order_item=order_item, url=mockup["mockup_url"]
                    )
                    order.mockups_for_order.add(themockup)

            if status=='pending':
                time.sleep(4)
                check_mockup_generation_status(order)
            if status=='failed':
                pass
        else:
            # Handle API request error
            print("Error:", response.text)
            return None


def send_alert_to_admin(message):
    # Send alert to admin (e.g., via email or notification)
    pass


# Example usage
def create_printful_order(order):
    # Define the endpoint URL
    url = "https://api.printful.com/orders"

    # Define the headers with the authorization token
    headers = {"Authorization": f"Bearer {settings.PRINTFUL_API_TOKEN}"}

    # Define an empty list to store item data
    items = []

    qr = order.user.qrcode_url

    # Iterate over each order item
    for order_item in order.shirts.all():
        item_data = {
            "variant_id": order_item.printful_variant_id,
            "quantity": order_item.quantity,
            "files": [
                {
                    "url": order_item.ordered_shirt.shirt_image_front_file,
                    "type": "front",
                },
                {
                "url":qr,
                "type":'sleeve_right',
                }
            ],
        }
        items.append(item_data)

    # Define the payload for the requ"?{exit}'/[es"t
    payload = {
        "recipient": {
            "name": f"{order.user.user.first_name} {order.user.user.last_name}",
            "address1": order.user.address,
            "city": order.user.city,
            "state_name": order.user.state,
            "state_code":'TX',
            "country_code": "US",
            "zip": order.user.zip,
        },
        "items": items,
    }

    try:
        print(payload)
        # Send the POST request to create the order
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes

        # Parse the JSON response
        order_data = response.json()
        printful_order_id = order_data['result']['id']

        # Return the Printful order ID
        return printful_order_id

    except requests.exceptions.RequestException as e:
        # Handle any exceptions or errors
        print(f"Error creating Printful order: {e}")
        try:
            error_data = response.json()
            print(f"Printful API error details: {error_data}")
        except (ValueError, json.decoder.JSONDecodeError):
            # Handle cases where the response isn't valid JSON
            pass
        return None
