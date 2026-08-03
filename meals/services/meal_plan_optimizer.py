import random
import copy
import math
from decimal import Decimal

def optimize_meal_plan(
    recipes,
    rules,
    total_meals=10,
    heat=3,
    starting_recipe=None,
    locked_recipes=None,
    forbidden_ids=None,
    debug=False,
):
    """
    recipes: list of Recipe objects with .id and .token_profile (dict[str, float])
    rules: dict of {token_type: minimum_required_amount}
    total_meals: number of meals in the plan
    heat: controls randomness (pick from top N scoring recipes at each step)
    starting_recipe: a Recipe object to use as first meal (optional)
    locked_recipes: list of Recipe objects to seed the plan with (optional).
        Generalizes starting_recipe to N recipes — used for "reoptimize
        everything except these" and, as the special case of locking every
        slot but one, "reoptimize just this one slot" (which naturally lands
        on the highest-pressure/last-step scoring since it's the only slot
        left to fill). Order among locked_recipes doesn't matter: token
        totals are a sum, not sequence-dependent — only the count seeded
        matters, for pacing the remaining picks against total_meals.
    forbidden_ids: set of recipe IDs to avoid repeats
    """
    forbidden_ids = set(forbidden_ids) if forbidden_ids else set()
    locked_recipes = list(locked_recipes) if locked_recipes else []

    if locked_recipes:
        for r in locked_recipes:
            forbidden_ids.add(r.id)
        available_recipes = [r for r in recipes if r.id not in forbidden_ids]
        pool_size = len({r.id for r in available_recipes}) + len(locked_recipes)
        if total_meals > pool_size:
            raise ValueError(
                f"Cannot build a plan of {total_meals} meals: only {pool_size} distinct recipes available."
            )
        if total_meals < len(locked_recipes):
            raise ValueError(
                f"total_meals ({total_meals}) is smaller than the number of locked recipes ({len(locked_recipes)})."
            )

        meal_plan = list(locked_recipes)
        token_progress = {}
        for r in meal_plan:
            token_progress = _merge_token_profiles(token_progress, r.token_profile)
    else:
        available_recipes = [r for r in recipes if r.id not in forbidden_ids]

        pool_size = len({r.id for r in available_recipes})
        if starting_recipe and starting_recipe.id not in {r.id for r in available_recipes}:
            pool_size += 1
        if total_meals > pool_size:
            raise ValueError(
                f"Cannot build a plan of {total_meals} meals: only {pool_size} distinct recipes available."
            )

        if starting_recipe:
            meal_plan = [starting_recipe]
            token_progress = copy.deepcopy(starting_recipe.token_profile)
        else:
            first = random.choice(available_recipes)
            meal_plan = [first]
            token_progress = copy.deepcopy(first.token_profile)

        forbidden_ids.add(meal_plan[0].id)

    for step in range(len(meal_plan), total_meals):
        candidates = [r for r in recipes if r.id not in forbidden_ids]
        # Shuffle so that candidates with tied scores (e.g. when rules is
        # empty) aren't always picked in recipe/DB order.
        random.shuffle(candidates)

        scored = []
        for recipe in candidates:
            simulated = _merge_token_profiles(token_progress, recipe.token_profile)
            score = _score_candidate(simulated, rules, step + 1, total_meals)
            scored.append((recipe, score))

        # Sort by score (lower is better)
        scored.sort(key=lambda x: x[1])
        top_n = scored[:min(heat, len(scored))]
        selected = random.choice(top_n)[0]

        meal_plan.append(selected)
        token_progress = _merge_token_profiles(token_progress, selected.token_profile)
        forbidden_ids.add(selected.id)

    if debug:
        return meal_plan, token_progress
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


def _recipe_sizing(serves, members):
    """
    Given a recipe's yield (`serves`) and the household's member count, decide
    how this recipe should be used for one batch:
      - too small (serves < members): multiply it up so it covers the
        household for the one occasion it's used in.
      - too big (serves > 3x members): only 3 occasions get eaten fresh (the
        in-fridge-leftovers safety window), the rest is frozen.
      - otherwise: no scaling needed, its yield covers `serves // members`
        occasions as ordinary (untracked) leftovers.
    Returns (multiplier, occasions, frozen_portions).
    """
    if serves < members:
        return math.ceil(members / serves), 1, 0

    threshold = 3 * members
    if serves > threshold:
        return 1, 3, serves - threshold

    return 1, serves // members, 0


def _ingredient_shortfall_penalty(ingredient_progress, forced_ingredients):
    """Score contribution for forced ingredients (see build_menu_batches's
    forced_ingredients param). Unlike token rules — whose target is prorated
    across the whole plan by _score_candidate — a forced ingredient's full
    target amount is treated as "due" from step one: the shortfall penalty
    stays at (roughly) its full size until the ingredient is used up, instead
    of easing in gradually. That's what makes forcing an ingredient behave
    greedily (grabbed as soon as a good recipe using it is available) rather
    than being spread evenly over the whole plan like a token rule.
    """
    if not forced_ingredients:
        return Decimal(0)
    penalty = Decimal(0)
    for ingredient_id, target in forced_ingredients.items():
        actual = ingredient_progress.get(ingredient_id, Decimal(0))
        penalty += max(Decimal(0), target - actual)
    return penalty


def build_menu_batches(
    recipes,
    rules,
    total_slots,
    members,
    heat=3,
    forbidden_ids=None,
    locked_recipes=None,
    forced_ingredients=None,
    debug=False,
):
    """
    Like optimize_meal_plan, but plans in servings-needed rather than
    recipes-needed: each pick becomes a "batch" that can cover 1-3 slots
    depending on how its yield (recipe._meal.serves) compares to `members`
    (see _recipe_sizing), instead of always covering exactly one slot.

    recipes: list of Recipe adapters (.id, .token_profile, ._meal.serves),
        optionally carrying .forced_ingredient_profile (dict {ingredient_id:
        Decimal grams used by this recipe} — see forced_ingredients below).
        Adapters without the attribute are treated as contributing nothing
        (getattr default {}), so callers/tests that don't care about forced
        ingredients don't need to set it.
    rules: dict of {token_type: minimum_required_amount}, same as optimize_meal_plan
    total_slots: number of day/meal-type slots to fill
    members: household member count driving the multiply-up/freeze rules
    forbidden_ids: recipe ids to exclude from fresh batch selection
    locked_recipes: recipes already pinned to a slot elsewhere (e.g. the
        preview flow's per-slot locks) — still sized via the same rule (a
        locked slot's multiplier/freeze is inherent to the recipe+household,
        not to how it was chosen) but excluded from being picked again as a
        fresh batch.
    forced_ingredients: optional dict {ingredient_id: Decimal grams wanted}.
        At every step, candidates are additionally scored on how much of
        each still-outstanding forced ingredient they'd use (see
        _ingredient_shortfall_penalty) — greedily, not prorated like token
        rules, so a forced ingredient tends to get used up in the first
        good-fitting recipes rather than spread across the whole plan.
        Locked recipes' usage counts toward the target too.

    Returns (batches, to_freeze), or (batches, to_freeze, token_progress,
    ingredient_progress) when debug=True:
      batches: ordered list of {"recipe": adapter, "occasions": int, "multiplier": int}
               whose occasions sum to total_slots, or fewer if there aren't
               enough distinct recipes to reach it (see below).
      to_freeze: list of {"recipe": adapter, "portions": int}

    Does NOT raise when there isn't enough distinct-recipe capacity to reach
    total_slots — no person wants a menu that repeats the same dish just to
    hit a slot count. Instead the picking loop stops once it runs out of
    candidates, so `sum(occasions for occasions in batches)` may come up
    short of total_slots; callers should treat that as "best effort" and
    tell the user what happened rather than treating it as an error.
    """
    forbidden_ids = set(forbidden_ids) if forbidden_ids else set()
    locked_recipes = list(locked_recipes) if locked_recipes else []
    forced_ingredients = forced_ingredients or {}

    batches = []
    to_freeze = []
    token_progress = {}
    ingredient_progress = {}
    slots_filled = 0

    for r in locked_recipes:
        forbidden_ids.add(r.id)
        multiplier, occasions, frozen = _recipe_sizing(r._meal.serves, members)
        token_progress = _merge_token_profiles(token_progress, r.token_profile)
        ingredient_progress = _merge_token_profiles(
            ingredient_progress, getattr(r, "forced_ingredient_profile", {})
        )
        if frozen:
            to_freeze.append({"recipe": r, "portions": frozen})
        batches.append({"recipe": r, "occasions": 1, "multiplier": multiplier})
        slots_filled += 1

    remaining_needed = total_slots - slots_filled
    if remaining_needed < 0:
        raise ValueError(
            f"total_slots ({total_slots}) is smaller than the number of locked recipes ({len(locked_recipes)})."
        )

    while slots_filled < total_slots:
        candidates = [r for r in recipes if r.id not in forbidden_ids]
        if not candidates:
            # Out of distinct recipes — stop here rather than repeating one.
            # slots_filled stays below total_slots; caller reports the gap.
            break
        # Shuffle so that candidates with tied scores (e.g. when rules is
        # empty) aren't always picked in recipe/DB order.
        random.shuffle(candidates)

        scored = []
        for recipe in candidates:
            simulated = _merge_token_profiles(token_progress, recipe.token_profile)
            score = _score_candidate(simulated, rules, slots_filled + 1, total_slots)
            if forced_ingredients:
                simulated_ingredients = _merge_token_profiles(
                    ingredient_progress, getattr(recipe, "forced_ingredient_profile", {})
                )
                score += _ingredient_shortfall_penalty(simulated_ingredients, forced_ingredients)
            scored.append((recipe, score))

        scored.sort(key=lambda x: x[1])
        top_n = scored[:min(heat, len(scored))]
        selected = random.choice(top_n)[0]

        multiplier, natural_occasions, frozen = _recipe_sizing(selected._meal.serves, members)
        occasions = min(natural_occasions, total_slots - slots_filled)
        # Only surface a freeze card when the 3x-cap is the actual reason for
        # not using the full yield — not when we simply ran out of slots.
        if frozen and occasions == natural_occasions:
            to_freeze.append({"recipe": selected, "portions": frozen})

        batches.append({"recipe": selected, "occasions": occasions, "multiplier": multiplier})
        token_progress = _merge_token_profiles(token_progress, selected.token_profile)
        ingredient_progress = _merge_token_profiles(
            ingredient_progress, getattr(selected, "forced_ingredient_profile", {})
        )
        forbidden_ids.add(selected.id)
        slots_filled += occasions

    if debug:
        return batches, to_freeze, token_progress, ingredient_progress
    return batches, to_freeze


def schedule_batches(batches):
    """
    Flattens batches (see build_menu_batches) into a chronologically-ordered
    list of length sum(occasions) — one entry per slot — using round-robin
    placement so a single recipe's occasions get spread out rather than
    dumped consecutively: no recipe is placed for a 3rd slot in a row unless
    it's the only batch with occasions left (unavoidable at that point).

    Returns a list of {"recipe": adapter, "multiplier": int}.
    """
    active = [
        {"recipe": b["recipe"], "multiplier": b["multiplier"], "remaining": b["occasions"]}
        for b in batches
        if b["occasions"] > 0
    ]

    result = []
    last_index = 0
    while active:
        n = len(active)
        chosen_i = None
        for step in range(n):
            i = (last_index + step) % n
            candidate = active[i]
            last_two_same = (
                len(result) >= 2
                and result[-1]["recipe"].id == candidate["recipe"].id
                and result[-2]["recipe"].id == candidate["recipe"].id
            )
            if last_two_same and n > 1:
                continue
            chosen_i = i
            break
        if chosen_i is None:
            chosen_i = last_index % n

        candidate = active[chosen_i]
        result.append({"recipe": candidate["recipe"], "multiplier": candidate["multiplier"]})
        candidate["remaining"] -= 1
        last_index = chosen_i + 1
        if candidate["remaining"] == 0:
            active.pop(chosen_i)
            last_index = chosen_i

    return result
