from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Ingredient, Household, HouseholdIngredient


@receiver(post_save, sender=Ingredient)
def create_household_ingredients_for_new_ingredient(sender, instance, created, **kwargs):
    if created:
        # Add this ingredient to all existing households
        for hh in Household.objects.all():
            HouseholdIngredient.objects.get_or_create(
                household=hh,
                ingredient=instance,
                defaults={"status": 0}  # or 2 if you prefer Plenty
            )


@receiver(post_save, sender=Household)
def create_ingredients_for_new_household(sender, instance, created, **kwargs):
    if created:
        # Add all ingredients for this new household
        for ing in Ingredient.objects.all():
            HouseholdIngredient.objects.get_or_create(
                household=instance,
                ingredient=ing,
                defaults={"status": 0}
            )
