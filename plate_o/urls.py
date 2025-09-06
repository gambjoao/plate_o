from django.contrib import admin
from django.urls import path
from meals.views import RandomMealsAPIView, MealIngredientsAPIView, MealsByIngredientsAPIView, MealTokensAPIView, HouseholdIngredientListView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/meals/<int:meal_id>/ingredients/', MealIngredientsAPIView.as_view(), name='meal-ingredients'),
    path('api/random-meals/', RandomMealsAPIView.as_view(), name='random-meals'),
    path('api/meals/by-ingredients/', MealsByIngredientsAPIView.as_view(), name='meals-by-ingredients'),
    path('api/meals/<int:meal_id>/tokens/', MealTokensAPIView.as_view(), name='meal-tokens'),
    path("api/pantry/<int:household_id>/ingredients/", HouseholdIngredientListView.as_view(), name="household-ingredients"),
]
