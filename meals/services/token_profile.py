from decimal import Decimal
from collections import defaultdict

def compute_menu_token_profile(meals):
    """
    Compute token totals for a list of meals. Each entry is either a Meal
    (multiplier defaults to 1) or a (meal, multiplier) tuple — pass the
    latter for menu slots whose yield was scaled up (MenuMeal.portions_multiplier)
    to cover the household, so token totals scale with it too.
    """
    from .token_calculator import compute_token_profile  # import inside to avoid circulars

    totals = defaultdict(Decimal)
    for entry in meals:
        meal, multiplier = entry if isinstance(entry, tuple) else (entry, 1)
        meal_tokens = compute_token_profile(meal, multiplier=multiplier)
        for token_name, value in meal_tokens.items():
            totals[token_name] += value

    return dict(totals)