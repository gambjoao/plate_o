import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from meals.models import Meal, MealIngredient, IngredientNutritionToken, IngredientMeasure, Household, HouseholdIngredient
from meals.serializers import MealIngredientSerializer, MealSerializer, HouseholdIngredientSerializer
from django.db.models import Count, Q
from decimal import Decimal, InvalidOperation
from .services.token_calculator import compute_token_profile


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
        serializer = HouseholdIngredientSerializer(ingredients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)