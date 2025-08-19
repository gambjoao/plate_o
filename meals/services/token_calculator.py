# services/token_profile.py
from decimal import Decimal, InvalidOperation
from ..models import MealIngredient, IngredientMeasure, IngredientNutritionToken

def compute_token_profile(meal):
    token_totals = {}
    meal_ingredients = MealIngredient.objects.select_related('ingredient').filter(meal=meal)

    for meal_ingredient in meal_ingredients:
        ingredient = meal_ingredient.ingredient

        try:
            quantity = Decimal(meal_ingredient.u_quantity)
        except (InvalidOperation, TypeError):
            continue

        unit = meal_ingredient.u_desc.strip().lower()

        try:
            measure = IngredientMeasure.objects.get(ingredient=ingredient, unit_description=unit)
            multiplier = Decimal(measure.multiplier)
        except IngredientMeasure.DoesNotExist:
            continue

        base_quantity = quantity * multiplier

        tokens = IngredientNutritionToken.objects.filter(ingredient=ingredient)
        for token in tokens:
            try:
                scaled_token = Decimal(token.quantity) * base_quantity
            except (InvalidOperation, TypeError):
                continue

            token_totals[token.token.name] = token_totals.get(token.token.name, Decimal(0)) + scaled_token
    print(token_totals)
    return token_totals
