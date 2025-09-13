from decimal import Decimal
from collections import defaultdict

def compute_menu_token_profile(meals):
    """
    Compute token totals for a list of meals.
    """
    from .token_calculator import compute_token_profile  # import inside to avoid circulars

    totals = defaultdict(Decimal)
    for meal in meals:
        meal_tokens = compute_token_profile(meal)
        for token_name, value in meal_tokens.items():
            totals[token_name] += value

    return dict(totals)