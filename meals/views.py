import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import HouseholdIngredient
from django.db import transaction
from django.utils import timezone
from .services.meal_plan_optimizer import optimize_meal_plan
from meals.models import MenuMeal

from meals.models import Meal, MealIngredient, IngredientNutritionToken, IngredientMeasure, Household, HouseholdIngredient
from meals.serializers import MealIngredientSerializer, MealSerializer, HouseholdIngredientSerializer
from django.db.models import Count, Q
from decimal import Decimal, InvalidOperation
from .services.token_calculator import compute_token_profile
from .models import Menu
from .serializers import MenuSerializer

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

        ingredients = HouseholdIngredient.objects.filter(household=household)
        ingredients_list = HouseholdIngredientSerializer(ingredients, many=True).data



        formatted_ingredients = {
            "Level 1": {
                "Level 2": {
                    "Level 3": [
                        {
                            "id": ing["ingredient_id"],
                            "name": ing["ingredient_name"],
                            "image": ing["ingredient_icon"],
                            "quantity": ing["status"]
                        }
                        for ing in ingredients_list
                    ]
                }
            }
        }

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
    
class GenerateMenuView(APIView):
    """
    POST endpoint to generate a new optimized menu for a household.
    """

    def post(self, request, *args, **kwargs):
        print("----------Got asked for new Menu----------")
        print(request.data)
        household_id = 1  # TODO: replace with real household logic
        days = int(request.data.get("days", 7))

        # Step 1: deactivate old menus
        Menu.objects.filter(household_id=household_id, is_active=True).update(is_active=False)

        # Step 2: fetch available recipes (wrap Meals into adapters for optimizer)
        recipes = []
        for meal in Meal.objects.all():
            adapter = type("RecipeAdapter", (), {})()
            adapter.id = meal.id
            adapter.name = meal.name
            adapter.token_profile = compute_token_profile(meal)
            adapter._meal = meal  # keep reference to real Meal object
            recipes.append(adapter)

        rules = {
            "red_meat": 2,  # example rule
        }

        meal_plan = optimize_meal_plan(
            recipes=recipes,
            rules=rules,
            total_meals=days,
            heat=3,
        )

        # Step 3: create new menu & insert menu meals
        with transaction.atomic():
            menu = Menu.objects.create(
                household_id=household_id,
                is_active=True,
                created_at=timezone.now()
            )

            for idx, recipe in enumerate(meal_plan, start=1):
                MenuMeal.objects.create(
                    menu=menu,
                    meal=recipe._meal,   # ✅ use real Meal instance, not adapter
                    day_number=idx,
                    meal_type=3,  # Dinner (hardcoded for now)
                    state="planned",
                )

        return Response({"detail": "Menu generated successfully."}, status=status.HTTP_201_CREATED)
