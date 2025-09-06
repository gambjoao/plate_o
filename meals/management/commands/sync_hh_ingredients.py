from django.core.management.base import BaseCommand
from meals.models import Household, Ingredient, HouseholdIngredient

class Command(BaseCommand):
    help = "Ensure every household has all ingredients in HouseholdIngredient table"

    def handle(self, *args, **options):
        created_count = 0
        for hh in Household.objects.all():
            for ing in Ingredient.objects.all():
                obj, created = HouseholdIngredient.objects.get_or_create(
                    household=hh,
                    ingredient=ing,
                    defaults={"status": 0},  # All Out by default
                )
                if created:
                    created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Sync complete. Added {created_count} missing HouseholdIngredient rows."
        ))
