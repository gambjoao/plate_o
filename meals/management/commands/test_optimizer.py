from django.core.management.base import BaseCommand
from meals.services.meal_plan_optimizer import optimize_meal_plan
from meals.services.token_calculator import compute_token_profile
from meals.models import Meal


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        recipes = list(Meal.objects.all())

        for recipe in recipes:
            recipe.token_profile = compute_token_profile(recipe)

        rules = {"red meat":2, "white meat": 2, "legumes": 2, "fish":2, "vegetables": 20}

        plan, tally = optimize_meal_plan(recipes, rules, total_meals=6, heat=3, debug=True)

        for i, meal in enumerate(plan):
            print(f"Meal {i+1}: {meal.name} (id: {meal.id})")
        print("Final token tally:", tally)
