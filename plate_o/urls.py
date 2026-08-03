from django.contrib import admin
from django.urls import path
from meals.views import RandomMealsAPIView, MealIngredientsAPIView, MealsByIngredientsAPIView, MealTokensAPIView, HouseholdIngredientListView, adjust_ingredient, CurrentMenuView, MenuIngredientsView, GenerateMenuView, RecipeDetailView, IngredientDetailView, OptimizeMenuPreviewView, CommitMenuView, MealSearchView, IngredientSearchView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/meals/<int:meal_id>/ingredients/', MealIngredientsAPIView.as_view(), name='meal-ingredients'),
    path('api/random-meals/', RandomMealsAPIView.as_view(), name='random-meals'),
    path('api/meals/by-ingredients/', MealsByIngredientsAPIView.as_view(), name='meals-by-ingredients'),
    path('api/meals/<int:meal_id>/tokens/', MealTokensAPIView.as_view(), name='meal-tokens'),
    path("api/pantry/<int:household_id>/ingredients/", HouseholdIngredientListView.as_view(), name="household-ingredients"),
    path('api/pantry/<int:household_id>/ingredients/<int:ingredient_id>/adjust/', adjust_ingredient),
    path('api/meals/<int:household_id>/current-menu/', CurrentMenuView.as_view(), name='current-menu'),
    path('api/meals/<int:household_id>/current-menu/ingredients/', MenuIngredientsView.as_view(), name='menu-ingredients'),
    path('api/meals/<int:household_id>/generate-menu/', GenerateMenuView.as_view(), name='generate-menu'),
    path('api/meals/<int:household_id>/optimize-preview/', OptimizeMenuPreviewView.as_view(), name='optimize-menu-preview'),
    path('api/meals/<int:household_id>/commit-menu/', CommitMenuView.as_view(), name='commit-menu'),
    path('api/meals/search/', MealSearchView.as_view(), name='meal-search'),
    path('api/recipes/<int:recipe_id>/', RecipeDetailView.as_view(), name='recipe-detail'),
    path('api/ingredients/', IngredientSearchView.as_view(), name='ingredient-search'),
    path('api/ingredients/<int:ingredient_id>/', IngredientDetailView.as_view(), name='ingredient-detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)