# services/token_profile.py
from decimal import Decimal, InvalidOperation
from ..models import MealIngredient, IngredientMeasure, IngredientNutritionToken

def compute_token_profile(meal, multiplier=1):
    token_totals = {}
    meal_ingredients = MealIngredient.objects.select_related('ingredient').filter(meal=meal)
    portions_multiplier = Decimal(multiplier)

    for meal_ingredient in meal_ingredients:
        ingredient = meal_ingredient.ingredient

        try:
            quantity = Decimal(meal_ingredient.u_quantity) * portions_multiplier
        except (InvalidOperation, TypeError):
            continue

        unit = meal_ingredient.u_desc.strip().lower()

        try:
            measure = IngredientMeasure.objects.get(ingredient=ingredient, unit_description=unit)
            unit_multiplier = Decimal(measure.multiplier)
        except IngredientMeasure.DoesNotExist:
            continue

        base_quantity = quantity * unit_multiplier

        tokens = IngredientNutritionToken.objects.filter(ingredient=ingredient)
        for token in tokens:
            try:
                scaled_token = Decimal(token.quantity) * base_quantity
            except (InvalidOperation, TypeError):
                continue

            token_totals[token.token.name] = token_totals.get(token.token.name, Decimal(0)) + scaled_token
    #print(token_totals)
    return token_totals


def compute_ingredient_quantities(meal, ingredient_ids):
    """Base-unit (g/ml/u, per Ingredient.base_unit) quantity of each requested
    ingredient this meal uses, via the same MealIngredient -> IngredientMeasure
    unit-conversion as compute_token_profile. Only computes for the given
    ingredient_ids (not every ingredient in the meal), since callers only ever
    care about a handful of "forced" ingredients per request. Same
    skip-on-missing-measure caveat as compute_token_profile: an ingredient
    whose recipe unit has no matching IngredientMeasure row contributes 0,
    silently. Returns {ingredient_id: Decimal}.
    """
    if not ingredient_ids:
        return {}

    totals = {}
    meal_ingredients = MealIngredient.objects.select_related('ingredient').filter(
        meal=meal, ingredient_id__in=list(ingredient_ids)
    )

    for meal_ingredient in meal_ingredients:
        ingredient = meal_ingredient.ingredient

        try:
            quantity = Decimal(meal_ingredient.u_quantity)
        except (InvalidOperation, TypeError):
            continue

        unit = meal_ingredient.u_desc.strip().lower()

        try:
            measure = IngredientMeasure.objects.get(ingredient=ingredient, unit_description=unit)
            unit_multiplier = Decimal(measure.multiplier)
        except IngredientMeasure.DoesNotExist:
            continue

        base_quantity = quantity * unit_multiplier
        totals[ingredient.id] = totals.get(ingredient.id, Decimal(0)) + base_quantity

    return totals
