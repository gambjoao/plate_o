from collections import defaultdict
from decimal import Decimal, InvalidOperation

from ..models import MealIngredient


def compute_menu_ingredients(menu):
    """
    Aggregate MealIngredient rows across every "planned" MenuMeal in a menu,
    scaling each meal's quantities by its slot's portions_multiplier and
    grouping by (ingredient, unit) so e.g. yogurt used as "1 cup" in one
    recipe and "3 tbsp" in another stays as two lines rather than being
    force-converted into a single base unit.

    Returns (measured, unmeasured):
    - measured: {ingredient_id: {"ingredient": Ingredient, "lines": {unit: Decimal}}}
    - unmeasured: {ingredient_id: Ingredient} — rows whose u_quantity isn't a
      parseable number (e.g. "qb"/"a gosto" for salt, curry, etc.). These
      still need to show up somewhere so a "to taste" ingredient never
      silently disappears from the list; an ingredient that also has a real
      measured line elsewhere is left out of this bucket.
    """
    measured = {}
    unmeasured = {}

    menu_meals = menu.menu_meals.filter(state="planned").select_related("meal")

    for menu_meal in menu_meals:
        multiplier = Decimal(menu_meal.portions_multiplier)
        meal_ingredients = MealIngredient.objects.select_related("ingredient").filter(
            meal=menu_meal.meal
        )

        for mi in meal_ingredients:
            ingredient = mi.ingredient
            unit = mi.u_desc.strip().lower()

            try:
                quantity = Decimal(mi.u_quantity) * multiplier
            except (InvalidOperation, TypeError):
                unmeasured.setdefault(ingredient.id, ingredient)
                continue

            bucket = measured.setdefault(
                ingredient.id, {"ingredient": ingredient, "lines": defaultdict(Decimal)}
            )
            bucket["lines"][unit] += quantity

    for ingredient_id in measured:
        unmeasured.pop(ingredient_id, None)

    return measured, unmeasured
