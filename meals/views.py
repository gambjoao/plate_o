import random
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import HouseholdIngredient
from django.db import transaction
from django.utils import timezone
from .services.meal_plan_optimizer import build_menu_batches, schedule_batches
from meals.models import MenuMeal, MenuFreezeEntry

from meals.models import Meal, Ingredient, MealIngredient, IngredientNutritionToken, IngredientMeasure, Household, HouseholdIngredient
from meals.serializers import MealIngredientSerializer, MealSerializer, HouseholdIngredientSerializer, RecipeSerializer, IngredientDetailSerializer, apply_multiplier_display
from django.db.models import Count, Q
from decimal import Decimal, InvalidOperation
from .services.token_calculator import compute_token_profile, compute_ingredient_quantities
from .services.token_profile import compute_menu_token_profile
from .models import Menu
from .serializers import MenuSerializer, serialize_menu_ingredients


def _build_recipe_adapters(forced_ingredient_ids=None):
    """Wrap every Meal in a lightweight adapter carrying its computed
    token_profile — the shape optimize_meal_plan expects (.id, .token_profile),
    plus a back-reference to the real Meal (._meal). Shared by GenerateMenuView
    and OptimizeMenuPreviewView so both run the optimizer over the same data.

    forced_ingredient_ids: optional list of ingredient ids to also compute a
    per-recipe forced_ingredient_profile for (dict {ingredient_id: Decimal
    grams used}) — see build_menu_batches's forced_ingredients param. Left
    empty/omitted this is just {} on every adapter (cheap no-op), since most
    callers don't have any forced ingredients."""
    recipes = []
    for meal in Meal.objects.all():
        adapter = type("RecipeAdapter", (), {})()
        adapter.id = meal.id
        adapter.name = meal.name
        adapter.token_profile = compute_token_profile(meal)
        adapter.forced_ingredient_profile = compute_ingredient_quantities(
            meal, forced_ingredient_ids or []
        )
        adapter._meal = meal  # keep reference to real Meal object
        recipes.append(adapter)
    return recipes


def _serialize_recipe_summary(meal):
    """Same nested-recipe shape as MenuSerializer.get_recipes's "recipe" object,
    minus the times_made placeholder (the frontend's Recipe model doesn't read
    it). Shared by OptimizeMenuPreviewView and MealSearchView."""
    return {
        "id": str(meal.id),
        "name": meal.name,
        "image": meal.image.name if meal.image else "",
        "cook_time": meal.time,
        "serves": meal.serves,
    }


def _parse_forced_ingredients(raw):
    """Parses the request's forcedIngredients field —
    [{"ingredient_id": 5, "grams": 500}, ...] — into {ingredient_id: Decimal
    grams}, summing duplicate ids. Returns (parsed, error_response);
    error_response is a Response to return as-is, None on success."""
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        return None, Response({"error": "forcedIngredients must be a list"}, status=status.HTTP_400_BAD_REQUEST)

    parsed = {}
    for entry in raw:
        try:
            ingredient_id = int(entry["ingredient_id"])
            grams = Decimal(str(entry["grams"]))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            return None, Response(
                {"error": "each forcedIngredients entry needs ingredient_id and a numeric grams"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if grams <= 0:
            return None, Response(
                {"error": "forcedIngredients grams must be positive"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        parsed[ingredient_id] = parsed.get(ingredient_id, Decimal(0)) + grams

    if parsed:
        existing_ids = set(Ingredient.objects.filter(id__in=parsed.keys()).values_list("id", flat=True))
        missing = set(parsed.keys()) - existing_ids
        if missing:
            return None, Response(
                {"error": f"Unknown ingredient_id(s): {sorted(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    return parsed, None


def _run_menu_optimizer(days, meals, rules, members, locked_recipes=None, recipes=None, forced_ingredients=None):
    """
    Shared by GenerateMenuView and OptimizeMenuPreviewView. Builds
    household-sized batches (see build_menu_batches: multiply-up small
    yields, freeze-cap oversized ones), schedules the freshly-picked batches
    round-robin (schedule_batches), then folds in any locked recipes at their
    fixed (day_number, meal_type) slot.

    locked_recipes: optional list of ((day_number, meal_type), recipe_adapter)
        pairs — that recipe is pinned to that exact slot instead of being
        freely scheduled.
    forced_ingredients: optional {ingredient_id: Decimal grams} — see
        build_menu_batches's param of the same name. When recipes isn't
        passed in, adapters are built with forced_ingredient_profile
        populated for exactly these ids.

    Returns (slots, assigned, to_freeze, recipes, unfilled_slots, ingredient_progress):
      slots: list of (day_number, meal_type) in chronological order
      assigned: dict {(day_number, meal_type): {"recipe", "multiplier", "locked"}}
        — only holds entries for slots that actually got filled.
      to_freeze: list of {"recipe": adapter, "portions": int}
      recipes: the recipe adapters used (so callers who resolved locked
        meal_ids against it beforehand don't need to rebuild it)
      unfilled_slots: (day_number, meal_type) entries left with no recipe
        because there weren't enough distinct recipes to reach `slots`
        (build_menu_batches never repeats one to force a fit) — empty in the
        common case. Chronologically last slots go unfilled first, since
        assignment walks `slots` in order and stops once the fresh queue
        runs dry.
      ingredient_progress: {ingredient_id: Decimal grams actually planned}
        across every batch picked (locked + fresh) — how much of each forced
        ingredient the resulting menu ended up using, for reporting back to
        the client. {} when forced_ingredients wasn't given.
    """
    total_slots = days * len(meals)
    slots = [(day, meal_type) for day in range(1, days + 1) for meal_type in meals]

    if recipes is None:
        recipes = _build_recipe_adapters(
            forced_ingredient_ids=list((forced_ingredients or {}).keys())
        )

    locked_recipes = locked_recipes or []
    locked_by_slot = dict(locked_recipes)
    locked_adapters = [adapter for _, adapter in locked_recipes]

    batches, to_freeze, _token_progress, ingredient_progress = build_menu_batches(
        recipes=recipes,
        rules=rules,
        total_slots=total_slots,
        members=members,
        heat=3,
        locked_recipes=locked_adapters,
        forced_ingredients=forced_ingredients,
        debug=True,
    )

    # Locked batches (occasions always 1, appended first by build_menu_batches)
    # map straight to their pinned slot; everything else is freely schedulable.
    # Note: spacing (no-3-in-a-row / freshness window) is computed only among
    # the freely-scheduled slots — locked slots are explicit user picks, so we
    # don't try to re-balance spacing around them.
    locked_ids = {a.id for a in locked_adapters}
    fresh_batches = [b for b in batches if b["recipe"].id not in locked_ids]
    fresh_queue = schedule_batches(fresh_batches)

    assigned = {}
    unfilled_slots = []
    for slot in slots:
        if slot in locked_by_slot:
            adapter = locked_by_slot[slot]
            multiplier = next(b["multiplier"] for b in batches if b["recipe"].id == adapter.id)
            assigned[slot] = {"recipe": adapter, "multiplier": multiplier, "locked": True}
        elif fresh_queue:
            entry = fresh_queue.pop(0)
            assigned[slot] = {"recipe": entry["recipe"], "multiplier": entry["multiplier"], "locked": False}
        else:
            unfilled_slots.append(slot)

    return slots, assigned, to_freeze, recipes, unfilled_slots, ingredient_progress


def _shortfall_payload(slots, unfilled_slots):
    """Optional "shortfall" field surfaced to the client when the optimizer
    couldn't fill every requested slot without repeating a recipe. None when
    everything got filled (the common case)."""
    if not unfilled_slots:
        return None
    filled = len(slots) - len(unfilled_slots)
    return {
        "requested_slots": len(slots),
        "filled_slots": filled,
        "message": (
            f"Só foi possível preencher {filled} de {len(slots)} refeições — "
            f"não há receitas suficientes para evitar repetir alguma. Adicione mais "
            f"receitas, ou reduza os dias/refeições, para preencher o resto."
        ),
    }

# Returns a given (input) amount of random recipe names
class RandomMealsAPIView(APIView):
    def get(self, request):
        try:
            amount = int(request.GET.get('amount', 5))
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        # Cap the amount between 1 and 50
        amount = max(1, min(amount, 50))

        meal_ids = list(Meal.objects.values_list('id', flat=True))
        sample_size = min(amount, len(meal_ids))
        selected_ids = random.sample(meal_ids, sample_size)

        meals_names = list(
            Meal.objects.filter(id__in=selected_ids).values_list('name', flat=True)
        )

        return Response({'meals': meals_names}, status=status.HTTP_200_OK)


# Returns the list of ingredients for a given meal
class MealIngredientsAPIView(APIView):
    def get(self, request, meal_id):
        meal = get_object_or_404(Meal, id=meal_id)
        ingredients = MealIngredient.objects.filter(meal=meal)
        serializer = MealIngredientSerializer(ingredients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    




#Returns recipes with inputed ingredients (list). The amount is also configurable
class MealsByIngredientsAPIView(APIView):
    def get(self, request):
        # Parse query params
        ingredient_ids = request.GET.get('ingredients', '')
        amount = request.GET.get('amount', 5)
        print(ingredient_ids)

        try:
            ingredient_ids = [int(i) for i in ingredient_ids.split(',') if i.strip().isdigit()]
            amount = int(amount)
        except ValueError:
            return Response({'error': 'Invalid ingredients or amount'}, status=status.HTTP_400_BAD_REQUEST)

        if not ingredient_ids:
            return Response({'error': 'No ingredient IDs provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Filter meals that contain ALL of the ingredients
        meals = (
            Meal.objects
            .annotate(matching_ingredients=Count('ingredients', filter=Q(ingredients__id__in=ingredient_ids), distinct=True))
            .filter(matching_ingredients=len(ingredient_ids))
        )

        meal_list = list(meals)
        random.shuffle(meal_list)
        selected_meals = meal_list[:amount]

        serializer = MealSerializer(selected_meals, many=True)
        return Response({
            'requested': amount,
            'returned': len(selected_meals),
            'recipes': serializer.data
        }, status=status.HTTP_200_OK)    

class MealTokensAPIView(APIView):
    def get(self, request, meal_id):
        try:
            meal = Meal.objects.get(pk=meal_id)
        except Meal.DoesNotExist:
            return Response({"error": "Meal not found."}, status=status.HTTP_404_NOT_FOUND)

        token_totals = compute_token_profile(meal)

        response = {k: float(v.quantize(Decimal("0.01"))) for k, v in token_totals.items()}
        return Response(response)
    
class HouseholdIngredientListView(APIView):
    def get(self, request, household_id):
        try:
            household = Household.objects.get(id=household_id)
        except Household.DoesNotExist:
            return Response({"error": "Household not found"}, status=status.HTTP_404_NOT_FOUND)

        ingredients = HouseholdIngredient.objects.filter(
            household=household
        ).select_related("ingredient", "ingredient__category")
        ingredients_list = HouseholdIngredientSerializer(ingredients, many=True).data

        # Nest each ingredient under its real IngredientCategory path (falls back
        # to a single "Uncategorized" bucket for ingredients with no category set).
        # A category that holds ingredients directly can't also have subcategories
        # of its own here — the last path segment's value is the ingredient list,
        # not another dict — so keep category assignments at leaf nodes.
        formatted_ingredients = {}
        for ing in ingredients_list:
            path = ing["category_path"]
            node = formatted_ingredients
            for level_name in path[:-1]:
                node = node.setdefault(level_name, {})
            node.setdefault(path[-1], []).append({
                "id": ing["ingredient_id"],
                "name": ing["ingredient_name"],
                "image": ing["ingredient_icon"],
                "quantity": ing["status"],
            })

        return Response(formatted_ingredients, status=status.HTTP_200_OK)

    
@api_view(['POST'])
def adjust_ingredient(request, household_id, ingredient_id):
    action = request.data.get('action')
    print(request.data)

    try:
        hi = HouseholdIngredient.objects.get(
            household_id=household_id,
            ingredient_id=ingredient_id
        )
        print(action)
    except HouseholdIngredient.DoesNotExist:
        return Response({"error": "Ingredient not found for this household."},
                        status=status.HTTP_404_NOT_FOUND)

    if action == "increment" and hi.status < 2:
        hi.status += 1
        hi.save()
    elif action == "decrement" and hi.status > 0:
        hi.status -= 1
        hi.save()
    else:
        return Response({"error": "Invalid action or status limit reached."},
                        status=status.HTTP_400_BAD_REQUEST)

    return Response({"status": hi.get_status_display()})

# Returns the current active menu for a household and its evaluation

class CurrentMenuView(APIView):
    def get(self, request, household_id):
        menu = Menu.objects.filter(household_id=household_id, is_active=True).first()
        if not menu:
            return Response({"detail": "No active menu found"}, status=404)

        serializer = MenuSerializer(menu)
        return Response(serializer.data)


class MenuIngredientsView(APIView):
    """All ingredients used by the active menu's planned meals, merged across
    recipes and grouped per unit (see serialize_menu_ingredients)."""

    def get(self, request, household_id):
        menu = Menu.objects.filter(household_id=household_id, is_active=True).first()
        if not menu:
            return Response({"detail": "No active menu found"}, status=404)

        return Response(serialize_menu_ingredients(menu, request))


class GenerateMenuView(APIView):
    """
    POST endpoint to generate a new optimized menu for a household.
    """

    MAX_DAYS = 30

    def post(self, request, *args, **kwargs):
        household_id = 1  # TODO: replace with real household logic
        days = int(request.data.get("days", 7))
        meals = request.data.get("meals", [2])  # default to lunch only
        rules = request.data.get("tokens", {})

        # Validate meals list
        if not meals or not isinstance(meals, list):
            return Response(
                {"error": "meals must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if days < 1 or days > self.MAX_DAYS:
            return Response(
                {"error": f"days must be between 1 and {self.MAX_DAYS}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        forced_ingredients, error = _parse_forced_ingredients(request.data.get("forcedIngredients"))
        if error:
            return error

        household = get_object_or_404(Household, id=household_id)

        # Step 1: deactivate old menus
        Menu.objects.filter(household_id=household_id, is_active=True).update(is_active=False)

        # Step 2: build household-sized batches and schedule them into slots
        try:
            slots, assigned, to_freeze, _recipes, unfilled_slots, _ingredient_progress = _run_menu_optimizer(
                days, meals, rules, household.number_of_members, forced_ingredients=forced_ingredients
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Step 3: create new menu & insert menu meals + freeze entries
        # (only for slots the optimizer actually filled — see unfilled_slots)
        with transaction.atomic():
            menu = Menu.objects.create(
                household_id=household_id,
                is_active=True,
                created_at=timezone.now()
            )

            for day_number, meal_type in slots:
                entry = assigned.get((day_number, meal_type))
                if entry is None:
                    continue
                MenuMeal.objects.create(
                    menu=menu,
                    meal=entry["recipe"]._meal,
                    day_number=day_number,
                    meal_type=meal_type,
                    state="planned",
                    portions_multiplier=entry["multiplier"],
                )

            for freeze in to_freeze:
                MenuFreezeEntry.objects.create(
                    menu=menu,
                    meal=freeze["recipe"]._meal,
                    portions=freeze["portions"],
                )

        response_body = {"detail": "Menu generated successfully."}
        shortfall = _shortfall_payload(slots, unfilled_slots)
        if shortfall:
            response_body["shortfall"] = shortfall

        return Response(response_body, status=status.HTTP_201_CREATED)


class OptimizeMenuPreviewView(APIView):
    """
    POST endpoint that runs the optimizer WITHOUT persisting anything, so the
    client can preview/edit a draft menu before committing it (CommitMenuView).
    Supports `locked`, a list of {day_number, meal_type, meal_id} slots to keep
    fixed — used for both "reoptimize everything except these" (locked = every
    slot the user pinned) and "reoptimize just this one slot" (locked = every
    *other* slot, computed client-side) — see optimize_meal_plan's
    locked_recipes param for why these are the same operation.
    """

    MAX_DAYS = 30

    def post(self, request, *args, **kwargs):
        household_id = 1  # TODO: replace with real household logic — ignored, same as elsewhere
        days = int(request.data.get("days", 7))
        meals = request.data.get("meals", [2])
        rules = request.data.get("tokens", {})
        locked = request.data.get("locked", [])

        if not meals or not isinstance(meals, list):
            return Response(
                {"error": "meals must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if days < 1 or days > self.MAX_DAYS:
            return Response(
                {"error": f"days must be between 1 and {self.MAX_DAYS}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not isinstance(locked, list):
            return Response({"error": "locked must be a list"}, status=status.HTTP_400_BAD_REQUEST)

        forced_ingredients, error = _parse_forced_ingredients(request.data.get("forcedIngredients"))
        if error:
            return error

        household = get_object_or_404(Household, id=household_id)
        slots = [(day, meal_type) for day in range(1, days + 1) for meal_type in meals]

        recipes = _build_recipe_adapters(forced_ingredient_ids=list(forced_ingredients.keys()))
        recipes_by_id = {r.id: r for r in recipes}

        locked_pairs = []
        for entry in locked:
            try:
                day_number = int(entry["day_number"])
                meal_type = int(entry["meal_type"])
                meal_id = int(entry["meal_id"])
            except (KeyError, TypeError, ValueError):
                return Response(
                    {"error": "each locked entry needs day_number, meal_type, meal_id"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if (day_number, meal_type) not in slots:
                return Response(
                    {"error": f"locked slot (day {day_number}, meal_type {meal_type}) is not part of this menu"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            adapter = recipes_by_id.get(meal_id)
            if adapter is None:
                return Response({"error": f"Unknown meal_id {meal_id}"}, status=status.HTTP_400_BAD_REQUEST)

            locked_pairs.append(((day_number, meal_type), adapter))

        try:
            _, assigned, to_freeze, _recipes, unfilled_slots, ingredient_progress = _run_menu_optimizer(
                days, meals, rules, household.number_of_members,
                locked_recipes=locked_pairs, recipes=recipes, forced_ingredients=forced_ingredients,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        meal_type_labels = dict(MenuMeal.MEAL_TYPE_CHOICES)
        today = timezone.localdate()

        result_recipes = []
        for day_number, meal_type in slots:
            entry = assigned.get((day_number, meal_type))
            if entry is None:
                continue
            recipe_summary = _serialize_recipe_summary(entry["recipe"]._meal)
            recipe_summary["name"] = apply_multiplier_display(recipe_summary["name"], entry["multiplier"])

            result_recipes.append({
                "day_number": day_number,
                "meal_type": meal_type,
                "meal_type_label": meal_type_labels.get(meal_type, "").lower(),
                "suggested_date": (today + timedelta(days=day_number - 1)).isoformat(),
                "locked": entry["locked"],
                "multiplier": entry["multiplier"],
                "recipe": recipe_summary,
            })

        token_totals = compute_menu_token_profile(
            [(assigned[slot]["recipe"]._meal, assigned[slot]["multiplier"]) for slot in slots if slot in assigned]
        )
        tokens_response = {
            token: {"real": float(value), "planned": 2}
            for token, value in token_totals.items()
        }

        to_freeze_response = [
            {
                "meal": _serialize_recipe_summary(freeze["recipe"]._meal),
                "portions": freeze["portions"],
            }
            for freeze in to_freeze
        ]

        response_body = {
            "tokens": tokens_response,
            "recipes": result_recipes,
            "to_freeze": to_freeze_response,
        }

        if forced_ingredients:
            names = {
                ing.id: ing.name
                for ing in Ingredient.objects.filter(id__in=forced_ingredients.keys())
            }
            response_body["forced_ingredients"] = [
                {
                    "ingredient_id": ingredient_id,
                    "name": names.get(ingredient_id, ""),
                    "requested_grams": float(target),
                    "planned_grams": float(ingredient_progress.get(ingredient_id, Decimal(0))),
                }
                for ingredient_id, target in forced_ingredients.items()
            ]

        shortfall = _shortfall_payload(slots, unfilled_slots)
        if shortfall:
            response_body["shortfall"] = shortfall

        return Response(response_body, status=status.HTTP_200_OK)


class CommitMenuView(APIView):
    """
    POST endpoint that persists an exact client-approved slot list as the new
    active menu — the save half of the draft flow (OptimizeMenuPreviewView is
    the generate/edit half). Doesn't run the optimizer at all: the client
    already decided the final {day_number, meal_type, meal_id} for every slot.
    """

    def post(self, request, *args, **kwargs):
        household_id = 1  # TODO: replace with real household logic
        entries = request.data.get("recipes", [])
        to_freeze_entries = request.data.get("to_freeze", [])

        if not entries or not isinstance(entries, list):
            return Response({"error": "recipes must be a non-empty list"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(to_freeze_entries, list):
            return Response({"error": "to_freeze must be a list"}, status=status.HTTP_400_BAD_REQUEST)

        parsed = []
        meal_ids = set()
        for entry in entries:
            try:
                day_number = int(entry["day_number"])
                meal_type = int(entry["meal_type"])
                meal_id = int(entry["meal_id"])
                multiplier = int(entry.get("multiplier", 1))
            except (KeyError, TypeError, ValueError):
                return Response(
                    {"error": "each recipe needs day_number, meal_type, meal_id"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            parsed.append((day_number, meal_type, meal_id, multiplier))
            meal_ids.add(meal_id)

        parsed_freeze = []
        for entry in to_freeze_entries:
            try:
                freeze_meal_id = int(entry["meal_id"])
                portions = int(entry["portions"])
            except (KeyError, TypeError, ValueError):
                return Response(
                    {"error": "each to_freeze entry needs meal_id, portions"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            parsed_freeze.append((freeze_meal_id, portions))
            meal_ids.add(freeze_meal_id)

        meals_by_id = {m.id: m for m in Meal.objects.filter(id__in=meal_ids)}
        missing = meal_ids - meals_by_id.keys()
        if missing:
            return Response({"error": f"Unknown meal_id(s): {sorted(missing)}"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            Menu.objects.filter(household_id=household_id, is_active=True).update(is_active=False)
            menu = Menu.objects.create(
                household_id=household_id,
                is_active=True,
                created_at=timezone.now()
            )
            for day_number, meal_type, meal_id, multiplier in parsed:
                MenuMeal.objects.create(
                    menu=menu,
                    meal=meals_by_id[meal_id],
                    day_number=day_number,
                    meal_type=meal_type,
                    state="planned",
                    portions_multiplier=multiplier,
                )
            for freeze_meal_id, portions in parsed_freeze:
                MenuFreezeEntry.objects.create(
                    menu=menu,
                    meal=meals_by_id[freeze_meal_id],
                    portions=portions,
                )

        return Response({"detail": "Menu committed successfully."}, status=status.HTTP_201_CREATED)


class IngredientSearchView(APIView):
    """Name search over all ingredients — powers the Optimizer's "force an
    ingredient into the plan" picker (IngredientForceBar/IngredientSelectionModal
    on the frontend). Same shape/convention family as MealSearchView below."""

    def get(self, request):
        query = request.GET.get('q', '').strip()
        try:
            amount = int(request.GET.get('amount', 30))
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        amount = max(1, min(amount, 100))

        ingredients = Ingredient.objects.all()
        if query:
            ingredients = ingredients.filter(name__icontains=query)
        ingredients = ingredients.order_by('name')[:amount]

        return Response({
            "ingredients": [
                {
                    "id": str(ing.id),
                    "name": ing.name,
                    "image": ing.icon.name if ing.icon else "",
                }
                for ing in ingredients
            ]
        })


class MealSearchView(APIView):
    """Name search over all recipes, for the draft menu's "replace via lookup" flow."""

    def get(self, request):
        query = request.GET.get('q', '').strip()
        try:
            amount = int(request.GET.get('amount', 20))
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        amount = max(1, min(amount, 50))

        meals = Meal.objects.all()
        if query:
            meals = meals.filter(name__icontains=query)
        meals = meals.order_by('name')[:amount]

        return Response({"recipes": [_serialize_recipe_summary(m) for m in meals]})


class RecipeDetailView(APIView):
    def get(self, request, recipe_id):
        meal = get_object_or_404(Meal, id=recipe_id)
        serializer = RecipeSerializer(meal, context={'request': request})
        return Response(serializer.data)


class IngredientDetailView(APIView):
    def get(self, request, ingredient_id):
        ingredient = get_object_or_404(Ingredient, id=ingredient_id)
        serializer = IngredientDetailSerializer(ingredient, context={'request': request})
        return Response(serializer.data)