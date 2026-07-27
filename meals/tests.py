from collections import Counter
from decimal import Decimal

from django.test import TestCase

from meals.services.meal_plan_optimizer import optimize_meal_plan


class FakeRecipe:
    def __init__(self, id, name, token_profile=None):
        self.id = id
        self.name = name
        self.token_profile = token_profile or {}


def make_recipes(n, token_profile=None):
    return [FakeRecipe(i, f"recipe-{i}", token_profile) for i in range(n)]


class OptimizeMealPlanTests(TestCase):
    def test_returns_requested_number_of_meals(self):
        recipes = make_recipes(10)
        plan = optimize_meal_plan(recipes, rules={}, total_meals=5, heat=3)
        self.assertEqual(len(plan), 5)

    def test_plan_has_no_duplicate_recipes(self):
        recipes = make_recipes(10)
        plan = optimize_meal_plan(recipes, rules={}, total_meals=10, heat=3)
        ids = [r.id for r in plan]
        self.assertEqual(len(ids), len(set(ids)))

    def test_raises_when_not_enough_recipes(self):
        recipes = make_recipes(3)
        with self.assertRaises(ValueError):
            optimize_meal_plan(recipes, rules={}, total_meals=5, heat=3)

    def test_raises_when_no_recipes_at_all(self):
        with self.assertRaises(ValueError):
            optimize_meal_plan([], rules={}, total_meals=1, heat=3)

    def test_empty_rules_does_not_always_pick_in_recipe_order(self):
        # Regression test: with no rules every candidate scores equally, so
        # a naive stable-sort would always select the first N recipes in
        # list order at every step. Run several plans and check the first
        # meal isn't the same recipe every time.
        recipes = make_recipes(20)
        first_meal_ids = {
            optimize_meal_plan(recipes, rules={}, total_meals=5, heat=3)[0].id
            for _ in range(30)
        }
        self.assertGreater(len(first_meal_ids), 1)

    def test_forbidden_ids_are_excluded(self):
        recipes = make_recipes(5)
        plan = optimize_meal_plan(
            recipes, rules={}, total_meals=3, heat=3, forbidden_ids={0, 1}
        )
        ids = {r.id for r in plan}
        self.assertFalse(ids & {0, 1})

    def test_starting_recipe_is_first_and_not_repeated(self):
        recipes = make_recipes(5)
        start = recipes[2]
        plan = optimize_meal_plan(
            recipes, rules={}, total_meals=4, heat=3, starting_recipe=start
        )
        self.assertEqual(plan[0].id, start.id)
        self.assertEqual(len([r for r in plan if r.id == start.id]), 1)

    def test_prefers_recipes_that_satisfy_rules(self):
        # One recipe fully satisfies the "vegetables" rule immediately,
        # the rest contribute nothing. With heat=1 the optimizer must be
        # fully greedy, so the high-value recipe should be picked first.
        recipes = make_recipes(5, token_profile={"vegetables": Decimal(0)})
        recipes[3].token_profile = {"vegetables": Decimal(100)}

        plan = optimize_meal_plan(
            recipes,
            rules={"vegetables": 10},
            total_meals=2,
            heat=1,
            starting_recipe=recipes[0],
        )
        self.assertEqual(plan[1].id, recipes[3].id)

    def test_debug_returns_token_tally(self):
        recipes = make_recipes(5, token_profile={"vegetables": Decimal(2)})
        plan, tally = optimize_meal_plan(
            recipes, rules={"vegetables": 1}, total_meals=3, heat=3, debug=True
        )
        self.assertEqual(len(plan), 3)
        self.assertEqual(tally["vegetables"], Decimal(6))
