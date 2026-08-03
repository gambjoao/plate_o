from rest_framework import serializers
from meals.models import Meal, Ingredient, IngredientNutritionToken, MealIngredient, HouseholdIngredient, MenuMeal, Menu, Tag
from datetime import timedelta
from meals.services.token_profile import compute_menu_token_profile
from meals.services.shopping_list import compute_menu_ingredients


def apply_multiplier_display(name, multiplier):
    """Appends an "x2"/"x3" suffix to a recipe's display name when its
    portions were multiplied up to cover the household for that slot."""
    if multiplier and multiplier > 1:
        return f"{name} x{multiplier}"
    return name


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
    category_path = serializers.SerializerMethodField()

    class Meta:
        model = HouseholdIngredient
        fields = [
            "ingredient_id",
            "ingredient_name",
            "ingredient_icon",
            "status",
            "status_display",
            "category_path",
        ]

    def get_category_path(self, obj):
        category = obj.ingredient.category
        return category.path_names() if category else ["Uncategorized"]



class RecipeSerializer(serializers.ModelSerializer):
    times_made = serializers.SerializerMethodField()

    class Meta:
        model = MenuMeal
        fields = [
            "id",  # menu_recipe_id
            "day_number",
            "meal_type",
            "state",
            "state_updated_at",
            "meal",
        ]

    def get_times_made(self, obj):
        return 7  # TODO: replace with household-based history later



class MenuSerializer(serializers.ModelSerializer):
    menu_id = serializers.IntegerField(source="id")
    user_id = serializers.IntegerField(source="household_id")
    generated_at = serializers.DateTimeField(source="created_at")
    tokens = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    to_freeze = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = [
            "menu_id",
            "user_id",
            "generated_at",
            "tokens",
            "recipes",
            "to_freeze",
        ]

    def get_tokens(self, obj):
        
        meals = [(mm.meal, mm.portions_multiplier) for mm in obj.menu_meals.all()]
        totals = compute_menu_token_profile(meals)

        # Example logic: "real" = actual, "planned" = dummy value
        return {
            token: {"real": float(value), "planned": 2}
            for token, value in totals.items()
        }

    def get_recipes(self, obj):
        recipes = []
        for menu_meal in obj.menu_meals.all().select_related("meal"):
            recipes.append(
                {
                    "menu_recipe_id": str(menu_meal.id),
                    "order_index": menu_meal.day_number,
                    "meal_type": menu_meal.get_meal_type_display().lower(),
                    "suggested_date": (
                        obj.created_at.date()
                        + timedelta(days=menu_meal.day_number - 1)
                    ).isoformat(),
                    "status": (
                        "ON_MENU" if menu_meal.state == "planned" else menu_meal.state.upper()
                    ),
                    "status_change_date": (
                        menu_meal.state_updated_at.isoformat()
                        if menu_meal.state_updated_at else None
                    ),
                    "recipe": {
                        "id": str(menu_meal.meal.id),
                        "name": apply_multiplier_display(menu_meal.meal.name, menu_meal.portions_multiplier),
                        "image": (
                            menu_meal.meal.image.name
                            if menu_meal.meal.image
                            else ""
                        ),
                        "cook_time": menu_meal.meal.time,
                        "serves": menu_meal.meal.serves,
                        "times_made": 7,  # placeholder
                    },
                }
            )
        return recipes

    def get_to_freeze(self, obj):
        return [
            {
                "meal": {
                    "id": str(entry.meal.id),
                    "name": entry.meal.name,
                    "image": entry.meal.image.name if entry.meal.image else "",
                    "cook_time": entry.meal.time,
                    "serves": entry.meal.serves,
                },
                "portions": entry.portions,
            }
            for entry in obj.freeze_entries.all().select_related("meal")
        ]



class IngredientInRecipeSerializer(serializers.Serializer):
    id = serializers.CharField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    image = serializers.SerializerMethodField()
    quantity = serializers.FloatField(source='u_quantity')
    unit = serializers.CharField(source='u_desc')

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.ingredient.icon:
            return request.build_absolute_uri(obj.ingredient.icon.url)
        return "assets/static_images/salmao.png"  # fallback placeholder


def _build_ingredient_icon_url(ingredient, request):
    if ingredient.icon:
        return request.build_absolute_uri(ingredient.icon.url)
    return "assets/static_images/salmao.png"  # fallback placeholder


def _clean_number(value):
    """Decimal(3.00) -> 3, Decimal(1.5) -> 1.5 — no trailing zeros in the JSON."""
    value = value.normalize()
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def serialize_menu_ingredients(menu, request):
    """Shopping-list payload for a menu's planned meals: quantities merged per
    (ingredient, unit) so the same ingredient can list multiple unit lines
    (e.g. "1 cup" + "3 tbsp"), plus a separate section for ingredients that
    only ever appear with a non-numeric quantity (e.g. "qb"/to taste)."""
    measured, unmeasured = compute_menu_ingredients(menu)

    measured_out = []
    for bucket in measured.values():
        ingredient = bucket["ingredient"]
        lines = [
            {"quantity": _clean_number(qty), "unit": unit}
            for unit, qty in sorted(bucket["lines"].items())
        ]
        measured_out.append({
            "ingredient_id": ingredient.id,
            "name": ingredient.name,
            "icon": _build_ingredient_icon_url(ingredient, request),
            "lines": lines,
        })
    measured_out.sort(key=lambda item: item["name"].lower())

    unmeasured_out = [
        {
            "ingredient_id": ingredient.id,
            "name": ingredient.name,
            "icon": _build_ingredient_icon_url(ingredient, request),
        }
        for ingredient in sorted(unmeasured.values(), key=lambda i: i.name.lower())
    ]

    return {"measured": measured_out, "unmeasured": unmeasured_out}


class TagSerializer(serializers.ModelSerializer):
    id = serializers.CharField()

    class Meta:
        model = Tag
        fields = ['id', 'name', 'category']


class InstructionSerializer(serializers.Serializer):
    step = serializers.IntegerField()
    instruction = serializers.CharField()


class RecipeSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    tokens = serializers.SerializerMethodField()
    ingredients = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    instructions = serializers.JSONField()

    class Meta:
        model = Meal
        fields = ['id', 'name', 'image', 'tokens', 'ingredients', 'tags', 'instructions']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return "assets/static_images/recipe_placeholder.jpg"

    def get_tokens(self, obj):
        token_totals = compute_menu_token_profile([obj])
        # Format: {"veggies": {"real": 42}, "fruits": {"real": 10}}
        formatted_tokens = {}
        for token_name, value in token_totals.items():
            formatted_tokens[token_name] = {"real": int(value)}
        return formatted_tokens

    def get_ingredients(self, obj):
        meal_ingredients = MealIngredient.objects.select_related('ingredient').filter(meal=obj)
        serializer = IngredientInRecipeSerializer(
            meal_ingredients, 
            many=True, 
            context=self.context
        )
        return serializer.data

    def get_tags(self, obj):
        return TagSerializer(obj.tags.all(), many=True).data


class IngredientDetailSerializer(serializers.ModelSerializer):
    """Backs GET /api/ingredients/<id>/ — same shape family as RecipeSerializer
    (id/name/image/tokens/...), consumed by the Flutter IngredientPage."""

    id = serializers.CharField()  # IngredientData.id is a Dart String, not int
    image = serializers.SerializerMethodField()
    tokens = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'image', 'tokens', 'quantity', 'recipes']

    def get_image(self, obj):
        return _build_ingredient_icon_url(obj, self.context.get('request'))

    def get_tokens(self, obj):
        rows = IngredientNutritionToken.objects.filter(ingredient=obj).select_related('token')
        return {row.token.name: {"real": _clean_number(row.quantity)} for row in rows}

    def get_quantity(self, obj):
        household_id = 1  # TODO: replace with real household logic, same as elsewhere
        household_stock = HouseholdIngredient.objects.filter(
            household_id=household_id, ingredient=obj
        ).first()
        return household_stock.status if household_stock else 0

    def get_recipes(self, obj):
        request = self.context.get('request')
        meals = Meal.objects.filter(ingredients=obj).distinct().order_by('name')
        return [
            {
                "id": str(meal.id),
                "name": meal.name,
                "image": (
                    request.build_absolute_uri(meal.image.url)
                    if meal.image else "assets/static_images/recipe_placeholder.jpg"
                ),
            }
            for meal in meals
        ]
