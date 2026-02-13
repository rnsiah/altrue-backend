import csv
from django.core.management.base import BaseCommand

from api.models import UserProfile

class Command(BaseCommand):
    help = 'Export UserProfile data to CSV'

    def handle(self, *args, **kwargs):
        # Define the output CSV file path
        csv_file_path = 'user_profiles.csv'  # Change to your desired path

        with open(csv_file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write the header row
            writer.writerow([
                'Stripe Customer ID', 
                'Payment Method ID', 
                'Username', 
                'Title', 
                'Description', 
                'DOB', 
                'Address', 
                'Country', 
                'City', 
                'State', 
                'Zip', 
                'Has Nonprofit', 
                'Has Company', 
                'Is Company Contributor', 
                'Is Nonprofit Contributor',
                'Altrue Level',
                'Slug'
            ])

            # Fetch and write UserProfile data
            for user_profile in UserProfile.objects.all():
                writer.writerow([
                    user_profile.stripe_customer_id,
                    user_profile.payment_method_id,
                    user_profile.username,
                    user_profile.title,
                    user_profile.description,
                    user_profile.dob,
                    user_profile.address,
                    user_profile.country,
                    user_profile.city,
                    user_profile.state,
                    user_profile.zip,
                    user_profile.has_nonprofit,
                    user_profile.has_company,
                    user_profile.is_companyContributor,
                    user_profile.is_nonprofitContributor,
                    user_profile.altrue_level.level_number if user_profile.altrue_level else None,  # Assuming altrue_level is a ForeignKey
                    user_profile.slug
                ])

        self.stdout.write(self.style.SUCCESS(f'Successfully exported UserProfile data to {csv_file_path}'))