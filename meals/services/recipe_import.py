from ..models import IngredientMeasure


def normalize_meal_ingredient_fields(u_quantity, u_desc, quantidade_desc, unit_desc):
    """quantidade_desc/unit_desc are just a human-readable copy of u_quantity/u_desc;
    default them when left blank so callers don't have to supply both."""
    u_desc = (u_desc or "").strip().lower()
    if not quantidade_desc:
        quantidade_desc = str(u_quantity) if u_quantity not in (None, "") else ""
    if not unit_desc:
        unit_desc = u_desc
    return quantidade_desc, unit_desc, u_desc


def measure_exists(ingredient, u_desc):
    return IngredientMeasure.objects.filter(
        ingredient=ingredient, unit_description=u_desc
    ).exists()
