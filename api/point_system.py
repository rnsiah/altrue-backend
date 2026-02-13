from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from Alt.models import  AltrueAction, AltrueActionCode, AltrueActionOnAggregate, AltrueLevel, AltruePointPromotion,  UserAltrueAction
import asyncio




def initialize_user_level(user_profile):
    """Initializes a user's Altrue level and sets up requirements for the next level."""
    # Set initial level
    initial_level = AltrueLevel.objects.get(level_number=0)
    user_profile.altrue_level = initial_level
    user_profile.save()

    # Get requirements for the next level
    next_level = AltrueLevel.objects.get(level_number=1)
    requirements = next_level.requiredActions.all()

    # Add requirements to user profile
    user_profile.requirementsForNextLevel.set(requirements)
    user_profile.save()

def calculate_points(user_altrue_action):
    """Calculates the points earned for a given user action.

    Args:
        user_altrue_action (UserAltrueAction): The completed user action.

    Returns:
        int: The number of points earned.
    """

    # Get the associated AltrueAction
    altrue_action = user_altrue_action.altrue_action

    # Calculate base points
    base_points = altrue_action.points_awarded

   # Check for active promotions
    active_promotions = AltruePointPromotion.objects.filter(is_active=True, altrueaction=altrue_action)

    # Apply promotions if any
    for promotion in active_promotions:
        base_points *= promotion.multiplier

    # Calculate final points
    final_points = base_points  # Adjust based on promotions or other factors

    return final_points


def update_user_points(user_altrue_action, calculated_points):
    from api.models import PointTransaction, AltruePoints
    """Updates the user's point balance based on calculated points.

    Args:
        user_altrue_action (UserAltrueAction): The completed user action.
        calculated_points (int): The points earned for the action.
    """
    user_profile = user_altrue_action.profile_acting
    # Get the user's AltruePoints record
    user_points = AltruePoints.objects.get(account=user_profile)

    # Update the point balance
    user_points.balance += calculated_points
    user_points.save()

    PointTransaction.objects.create(
        user=user_profile,
        action=user_altrue_action.altrue_action,
        amount=calculated_points,
        balance_after=user_points.balance + calculated_points,
    )
    
    if check_level_up(user_profile):
        update_user_level(user_profile)


def check_level_up(user_profile):
    """Checks if a user has met the requirements for the next level.

    Args:
        user_profile (UserProfile): The user's profile.

    Returns:
        bool: True if the user has leveled up, False otherwise.
    """
    
    current_level = user_profile.altrue_level
    try:
        next_level = AltrueLevel.objects.get(level_number=current_level.level_number + 1)
    except AltrueLevel.DoesNotExist:
        return False
    # Check point requirement
    if user_profile.altrue_points.balance < next_level.minimum_points:
        return False

    # Check action requirements
    required_actions = current_level.requiredActions.all()
    completed_actions = user_profile.useraltrueaction_set.values_list('altrue_action_id', flat=True)
    if set(required_actions.values_list('id', flat=True)) - set(completed_actions):
        return False

    # User has met all requirements
    return True


# def is_first_time_action(userprofile, action_code):
#     """Checks for all first time actions done by the user

#     Args:
#         userprofile(UserProfile): The User Profile Object.
#         action_code (str): The code of the action to check.
    
#     Returns:
#         bool: True if the action is performed for the first time. False otherwise
#     """
#     if action_code == 'makeADonation':
#         exists = UserDonation.objects.filter(user = userprofile)
#         if exists.count()==1:
#             action = AltrueAction.objects.get(action_code__='firstUserDonation')
#             first_donation = UserAltrueAction.objects.create(profile_acting = userprofile, )
            



def update_user_level(user_profile):
    """Updates the user's level if they've met the requirements.

    Args:
        user_profile (UserProfile): The user's profile.
    """

    if check_level_up(user_profile):
        current_level = user_profile.altrue_level
        try:
            next_level = AltrueLevel.objects.get(level_number=current_level.level_number + 1)
        except AltrueLevel.DoesNotExist:
            return
        
        user_profile.altrue_level = next_level
        user_profile.save()

        # Clear existing requirements and add new ones
        user_profile.requirementsForNextLevel.clear()
        user_profile.requirementsForNextLevel.add(*next_level.requiredActions.all()) 


def record_user_action(user_profile, action_code, action_data):
    try:
        actions = []
        altrue_action_code = AltrueActionCode.objects.get(code=action_code)

        altrue_action = AltrueAction.objects.get(action_code=altrue_action_code)


        ##Check if the user has already reached the maximum number of occurrences for the Altrue Action
        existing_user_actions = UserAltrueAction.objects.filter(profile_acting = user_profile, altrue_action = altrue_action)
        
        if existing_user_actions.count() is None or existing_user_actions.count() < altrue_action.number_of_occurrences:
            print(True)
            user_altrue_action = UserAltrueAction.objects.create(profile_acting = user_profile,
                                                            altrue_action=altrue_action)
            print(user_altrue_action)
            calculated_points = calculate_points(user_altrue_action)
            print(calculated_points)
            update_user_points( user_altrue_action, calculated_points)
            actions = [user_altrue_action]
        agg_action = check_aggregate_actions(user_profile, altrue_action)
        if agg_action:
            actions.append(agg_action)
        
        return actions
        
        

    except Exception as e:
        print(f"An error occurred: {e}")

def donationSumCheck(user_profile, user_action):
    from api.models import UserDonation
    """Checks to see the aggregate amounts of donations that are made by the user, in order 
    to determine if they qualify for the rewards associated with donation sums
    
    Args:
        user_profile (UserProfile): The user's profile.

        user_action (UserAltrueAction): The users action that we are deciding on.
    """
    donation_sum = 0
    if user_action.altrue_action.action.action_type.code == 'donation':
        total_donations = UserDonation.objects.filter(user = user_profile)
        for donation in total_donations:
            donation_sum += donation.dollar_amount
            
        if donation_sum >=25:
            record_user_action()
                
        if donation_sum >= 100:
            record_user_action()
        
        if donation_sum >=100:
            record_user_action()

        if donation_sum >=250:
            record_user_action()

        if donation_sum>=500:
            record_user_action()
        
    

    
    # Check to see if the action is in any of the aggregate actions
def check_aggregate_actions(user_profile, altrue_action):
    # If the action is an action that you have to do multipple times.
    # An example would dbe makeADonation and make 100 donations.
    aggregate_actions = AltrueActionOnAggregate.objects.filter(aggregate_action = altrue_action)
    completed_actions=[]
    for the_altrue_action in aggregate_actions:
        is_promoted = the_altrue_action.altrue_action.is_promoted
        user_action_taken, created = UserAltrueAction.objects.get_or_create(
            altrue_action = the_altrue_action.altrue_action,
            profile_acting = user_profile, 
            is_aggregate = True,
            is_promotion = is_promoted,
            defaults={'aggregate_complete_date': None}
        )
        user_action_taken.count += 1
        user_action_taken.save()

        if user_action_taken.count == the_altrue_action.altrue_action.aggregate_count:
            print(True)
            points_awarded = calculate_points(user_action_taken)
            update_user_points(user_action_taken, points_awarded)
            user_action_taken.aggregate_complete_date = timezone.now()
            user_action_taken.save()
            completed_actions.append(user_action_taken)
        
    return completed_actions if completed_actions else None
        
            
            # Award aggregate reward
            # ...


# def award_aggregate_reward(user_profile, action, theUsersAction):
#     """
#     Awards the reward for a completed aggregate action.

#     Args:
#         user_profile (UserProfile): The user profile of the acting user.
#         action (AltrueActionOnAggregate): The completed aggregate action.
#     """

#     # Access the aggregate action itself
#     aggregate_altrue_action = action.altrue_action

#     # Award points for completing the aggregate action
#     calculatecalculate_points(aggregate_altrue_action)

#     update_user_points

#     # Create a point transaction for the aggregate reward
#     PointTransaction.objects.create(
#         user=user_profile,
#         action=None,  # Or create a specific action for aggregate rewards
#         amount=aggregate_altrue_action.points_awarded,
#         balance_after=user_profile.altrue_points.balance,
#         is_promotion=False
#     )

#     # Additional logic for other reward types (e.g., badges, notifications)
#     # ...