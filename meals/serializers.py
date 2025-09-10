from rest_framework import serializers
from meals.models import Meal, Ingredient, MealIngredient, HouseholdIngredient



class MealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meal
        fields = ['id', 'name']

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name']

class MealIngredientSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer()

    class Meta:
        model = MealIngredient
        fields = ['ingredient', 'quantidade_desc', 'unit_desc', 'u_quantity', 'u_desc', 'sub', 'notas', 'required']

class HouseholdIngredientSerializer(serializers.ModelSerializer):
    ingredient_id = serializers.CharField(source="ingredient.id")
    ingredient_name = serializers.CharField(source="ingredient.name")
    ingredient_icon = serializers.CharField(source="ingredient.icon")
    status_display = serializers.CharField(source="get_status_display")

    class Meta:
        model = HouseholdIngredient
        fields = ["ingredient_id", "ingredient_name", "ingredient_icon", "status", "status_display"]



