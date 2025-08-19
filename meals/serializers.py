from rest_framework import serializers
from meals.models import Meal, Ingredient, MealIngredient



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


