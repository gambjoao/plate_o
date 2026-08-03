from collections import Counter
from decimal import Decimal

from django.test import TestCase

from meals.services.meal_plan_optimizer import (
    optimize_meal_plan,
    build_menu_batches,
    schedule_batches,
)


class FakeMeal:
    def __init__(self, serves):
        self.serves = serves


class FakeRecipe:
    def __init__(self, id, name, token_profile=None, serves=2, forced_ingredient_profile=None):
        self.id = id
        self.name = name
        self.token_profile = token_profile or {}
        self.forced_ingredient_profile = forced_ingredient_profile or {}
        self._meal = FakeMeal(serves)


def make_recipes(n, token_profile=None, serves=2):
    return [FakeRecipe(i, f"recipe-{i}", token_profile, serves=serves) for i in range(n)]


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

    def test_locked_recipes_stay_in_plan_and_fill_the_rest(self):
        recipes = make_recipes(5)
        locked = [recipes[1], recipes[3]]
        plan = optimize_meal_plan(
            recipes, rules={}, total_meals=4, heat=3, locked_recipes=locked
        )
        self.assertEqual(len(plan), 4)
        locked_ids = {r.id for r in locked}
        plan_ids = [r.id for r in plan]
        # both locked recipes are present, and nothing repeats
        self.assertTrue(locked_ids.issubset(set(plan_ids)))
        self.assertEqual(len(plan_ids), len(set(plan_ids)))

    def test_locked_recipes_raises_when_not_enough_recipes_left(self):
        recipes = make_recipes(3)
        with self.assertRaises(ValueError):
            optimize_meal_plan(
                recipes,
                rules={},
                total_meals=5,
                heat=3,
                locked_recipes=[recipes[0]],
            )


class BuildMenuBatchesTests(TestCase):
    def test_small_serves_gets_multiplied_up_to_cover_members(self):
        recipes = [FakeRecipe(1, "Soup", serves=1)]
        batches, to_freeze = build_menu_batches(recipes, rules={}, total_slots=1, members=4)
        self.assertEqual(batches[0]["multiplier"], 4)
        self.assertEqual(batches[0]["occasions"], 1)
        self.assertEqual(to_freeze, [])

    def test_moderate_serves_covers_multiple_occasions_without_freezing(self):
        recipes = [FakeRecipe(1, "Stew", serves=4)]
        batches, to_freeze = build_menu_batches(recipes, rules={}, total_slots=2, members=2)
        self.assertEqual(batches[0]["occasions"], 2)
        self.assertEqual(batches[0]["multiplier"], 1)
        self.assertEqual(to_freeze, [])

    def test_oversized_serves_caps_at_three_occasions_and_freezes_rest(self):
        recipes = [FakeRecipe(1, "Feijoada", serves=10)]
        batches, to_freeze = build_menu_batches(recipes, rules={}, total_slots=3, members=2)
        self.assertEqual(batches[0]["occasions"], 3)
        self.assertEqual(len(to_freeze), 1)
        self.assertEqual(to_freeze[0]["portions"], 4)  # 10 - 3*2

    def test_total_occasions_sum_to_total_slots(self):
        recipes = make_recipes(10, serves=2)
        batches, _ = build_menu_batches(recipes, rules={}, total_slots=10, members=2)
        self.assertEqual(sum(b["occasions"] for b in batches), 10)

    def test_no_recipe_repeated_across_batches(self):
        recipes = make_recipes(10, serves=2)
        batches, _ = build_menu_batches(recipes, rules={}, total_slots=10, members=2)
        ids = [b["recipe"].id for b in batches]
        self.assertEqual(len(ids), len(set(ids)))

    def test_fills_what_it_can_when_not_enough_capacity(self):
        # 2 recipes, each covering exactly 1 occasion (serves == members) —
        # can't cover 5 slots. Rather than raise, it should fill the 2 it can
        # and stop (no person wants a menu that repeats a dish to hit a count).
        recipes = make_recipes(2, serves=2)
        batches, to_freeze = build_menu_batches(recipes, rules={}, total_slots=5, members=2)
        self.assertEqual(sum(b["occasions"] for b in batches), 2)
        ids = [b["recipe"].id for b in batches]
        self.assertEqual(len(ids), len(set(ids)))

    def test_locked_recipes_still_raise_when_total_slots_too_small(self):
        # This one stays a hard error: it's an inconsistent request (more
        # locked recipes than slots), not a capacity shortfall to degrade.
        locked = [FakeRecipe(1, "A", serves=2), FakeRecipe(2, "B", serves=2)]
        with self.assertRaises(ValueError):
            build_menu_batches([], rules={}, total_slots=1, members=2, locked_recipes=locked)

    def test_locked_recipe_is_sized_and_excluded_from_fresh_batches(self):
        locked = FakeRecipe(99, "Locked Soup", serves=1)
        fresh = make_recipes(3, serves=2)
        batches, _ = build_menu_batches(
            fresh, rules={}, total_slots=4, members=4, locked_recipes=[locked]
        )
        locked_batch = next(b for b in batches if b["recipe"].id == locked.id)
        self.assertEqual(locked_batch["multiplier"], 4)
        self.assertEqual(locked_batch["occasions"], 1)
        # locked recipe wasn't also picked fresh
        ids = [b["recipe"].id for b in batches]
        self.assertEqual(ids.count(locked.id), 1)

    def test_forced_ingredient_is_greedily_preferred(self):
        # One recipe carries a big dose of the forced ingredient, the rest
        # carry none. With heat=1 the optimizer is fully greedy, so the
        # ingredient-heavy recipe should be picked first even though there's
        # no token rule pushing it there.
        recipes = make_recipes(5, serves=2)
        recipes[3].forced_ingredient_profile = {7: Decimal(1000)}

        batches, _, _token_progress, ingredient_progress = build_menu_batches(
            recipes,
            rules={},
            total_slots=2,
            members=2,
            heat=1,
            forced_ingredients={7: Decimal(500)},
            debug=True,
        )
        self.assertEqual(batches[0]["recipe"].id, recipes[3].id)
        self.assertEqual(ingredient_progress[7], Decimal(1000))

    def test_forced_ingredients_not_in_any_recipe_do_not_crash(self):
        recipes = make_recipes(3, serves=2)
        batches, to_freeze = build_menu_batches(
            recipes, rules={}, total_slots=2, members=2, forced_ingredients={42: Decimal(500)}
        )
        self.assertEqual(sum(b["occasions"] for b in batches), 2)

    def test_locked_recipe_ingredient_usage_counts_toward_forced_target(self):
        locked = FakeRecipe(99, "Locked", serves=2, forced_ingredient_profile={7: Decimal(300)})
        fresh = make_recipes(2, serves=2)
        _, _, _token_progress, ingredient_progress = build_menu_batches(
            fresh,
            rules={},
            total_slots=2,
            members=2,
            locked_recipes=[locked],
            forced_ingredients={7: Decimal(300)},
            debug=True,
        )
        self.assertEqual(ingredient_progress[7], Decimal(300))


class ScheduleBatchesTests(TestCase):
    def test_returns_one_entry_per_occasion(self):
        recipe_a = FakeRecipe(1, "A", serves=6)
        recipe_b = FakeRecipe(2, "B", serves=2)
        batches = [
            {"recipe": recipe_a, "occasions": 3, "multiplier": 1},
            {"recipe": recipe_b, "occasions": 1, "multiplier": 1},
        ]
        scheduled = schedule_batches(batches)
        self.assertEqual(len(scheduled), 4)

    def test_no_three_consecutive_identical_slots_when_avoidable(self):
        # Two batches with comparable occasion counts round-robin cleanly,
        # so no recipe should ever need to repeat 3 times in a row.
        recipe_a = FakeRecipe(1, "A", serves=6)
        recipe_b = FakeRecipe(2, "B", serves=6)
        batches = [
            {"recipe": recipe_a, "occasions": 3, "multiplier": 1},
            {"recipe": recipe_b, "occasions": 3, "multiplier": 1},
        ]
        scheduled = schedule_batches(batches)
        for i in range(len(scheduled) - 2):
            ids = {scheduled[i]["recipe"].id, scheduled[i + 1]["recipe"].id, scheduled[i + 2]["recipe"].id}
            self.assertGreater(len(ids), 1)
