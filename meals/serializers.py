from rest_framework import serializers
from meals.models import Meal, Ingredient, MealIngredient, HouseholdIngredient, MenuMeal, Menu
from datetime import timedelta
from meals.services.token_profile import compute_menu_token_profile


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

    class Meta:
        model = Menu
        fields = [
            "menu_id",
            "user_id",
            "generated_at",
            "tokens",
            "recipes",
        ]

    def get_tokens(self, obj):
        
        meals = [mm.meal for mm in obj.menu_meals.all()]
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
                        "name": menu_meal.meal.name,
                        "image": (
                            menu_meal.meal.image.name
                            if menu_meal.meal.image
                            else ""
                        ),
                        "cook_time": menu_meal.meal.time,
                        "times_made": 7,  # placeholder
                    },
                }
            )
        return recipes
    


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


class TagSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class InstructionSerializer(serializers.Serializer):
    step = serializers.IntegerField()
    instruction = serializers.CharField()


class RecipeSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    tokens = serializers.SerializerMethodField()
    ingredients = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    instructions = serializers.SerializerMethodField()

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
        # Hardcoded for now as requested
        return [
            {"id": "1", "name": "tag 1"},
            {"id": "2", "name": "tag 2"}
        ]

    def get_instructions(self, obj):
        # Parse instructions field - split by pattern like "1 - ", "2 - ", etc.
        instructions_text = obj.instructions or "1 - placeholder"
        
        steps = []
        lines = instructions_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line starts with "number - "
            parts = line.split(' - ', 1)
            if len(parts) == 2 and parts[0].strip().isdigit():
                step_num = int(parts[0].strip())
                instruction_text = parts[1].strip()
                steps.append({
                    "step": step_num,
                    "instruction": instruction_text
                })
            else:
                # If no pattern found, treat as step 1
                if not steps:
                    steps.append({
                        "step": 1,
                        "instruction": line
                    })
        
        # If still empty, add placeholder
        if not steps:
            steps.append({
                "step": 1,
                "instruction": "placeholder"
            })
        
        return steps