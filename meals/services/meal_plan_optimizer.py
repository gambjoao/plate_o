import random
import copy
from decimal import Decimal

def optimize_meal_plan(
    recipes,
    rules,
    total_meals=10,
    heat=3,
    starting_recipe=None,
    forbidden_ids=None,
    debug=False,
):
    """
    recipes: list of Recipe objects with .id and .token_profile (dict[str, float])
    rules: dict of {token_type: minimum_required_amount}
    total_meals: number of meals in the plan
    heat: controls randomness (pick from top N scoring recipes at each step)
    starting_recipe: a Recipe object to use as first meal (optional)
    forbidden_ids: set of recipe IDs to avoid repeats
    """
    print(f"!!!!!!!!!!!!!!!!!!Optimizing meal plan for {total_meals} meals with heat {heat}")
    forbidden_ids = set(forbidden_ids) if forbidden_ids else set()
    available_recipes = [r for r in recipes if r.id not in forbidden_ids]

    if starting_recipe:
        meal_plan = [starting_recipe]
        token_progress = copy.deepcopy(starting_recipe.token_profile)
    else:
        first = random.choice(available_recipes)
        meal_plan = [first]
        token_progress = copy.deepcopy(first.token_profile)

    forbidden_ids.add(meal_plan[0].id)

    for step in range(1, total_meals):
        candidates = [r for r in recipes if r.id not in forbidden_ids]

        scored = []
        for recipe in candidates:
            simulated = _merge_token_profiles(token_progress, recipe.token_profile)
            score = _score_candidate(simulated, rules, step + 1, total_meals)
            scored.append((recipe, score))

        # Sort by score (lower is better)
        scored.sort(key=lambda x: x[1])
        top_n = scored[:min(heat, len(scored))]
        print(top_n)
        selected = random.choice(top_n)[0]
        print(selected.name)
        print(selected.token_profile)

        meal_plan.append(selected)
        token_progress = _merge_token_profiles(token_progress, selected.token_profile)
        forbidden_ids.add(selected.id)

    if debug:
        return meal_plan, token_progress
    print(token_progress)
    print("Final meal plan:")
    for meal in meal_plan:
        print(f"- {meal.name}")
    return meal_plan


def _merge_token_profiles(base, addition):
    result = copy.deepcopy(base)
    for token, value in addition.items():
        result[token] = result.get(token, 0) + value
    return result


def _score_candidate(token_progress, rules, current_step, total_steps):
    """
    Penalize based on how far under the expected token amount we are.
    Only penalize underperformance for now.
    """
    penalty = 0
    for token, required in rules.items():
        expected = Decimal(current_step) / Decimal(total_steps) * Decimal(required)
        actual = token_progress.get(token, Decimal(0))
        under = max(Decimal(0), expected - actual)
        penalty += under
    return penalty
