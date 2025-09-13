from django.db import models

class Ingredient(models.Model):
    name = models.CharField(max_length=255)
    base_unit = models.CharField(
        max_length=10,
        choices=[
            ('g', 'Grams'),
            ('ml', 'Milliliters'),
            ('u', 'Unit')
        ],
    )
    portion_description = models.CharField(max_length=100, null=True, blank=True)
    icon = models.ImageField(upload_to='ingredient_icons/', null=True, blank=True)

    def __str__(self):
        return self.name
    
    
class Meal(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    instructions = models.TextField()
    serves = models.PositiveIntegerField()
    overnight_prep = models.BooleanField(default=False)
    time = models.PositiveIntegerField(help_text="Time in minutes")
    nuisance_factor = models.FloatField()
    image = models.ImageField(upload_to='meal_images/', null=True, blank=True)
    ingredients = models.ManyToManyField(
        Ingredient,
        through='MealIngredient',
        related_name='meals'
    )

    def __str__(self):
        return self.name
    
class MealIngredient(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantidade_desc = models.CharField(max_length=100, blank=True)
    unit_desc = models.CharField(max_length=100, blank=True)
    u_quantity = models.CharField(max_length=100, blank=True)
    u_desc = models.CharField(max_length=100, blank=True)
    sub = models.CharField(max_length=255, blank=True, null=True)
    notas = models.TextField(blank=True, null=True)
    required = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.meal} - {self.ingredient}"

class IngredientMeasure(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='unit_conversions')
    unit_description = models.CharField(max_length=10)  # e.g. 'tbsp', 'c', 'qb'
    multiplier = models.FloatField(help_text="Multiply this by the quantity to get value in base unit")

    class Meta:
        unique_together = ('ingredient', 'unit_description')  # Prevent duplicate rows

    def __str__(self):
        return f"{self.ingredient.name} - {self.unit_description}"
    

class NutritionToken(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
class IngredientNutritionToken(models.Model):
    ingredient = models.ForeignKey('Ingredient', on_delete=models.CASCADE)
    token = models.ForeignKey('NutritionToken', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ('ingredient', 'token')

class Household(models.Model):
    name = models.CharField(max_length=255, default="Default Household")

    def __str__(self):
        return self.name

class HouseholdIngredient(models.Model):
    STATUS_CHOICES = [
        (0, "All Out"),
        (1, "Low"),
        (2, "Plenty"),
    ]

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="ingredients")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="household_stock")
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=0)

    class Meta:
        unique_together = ("household", "ingredient")

    def __str__(self):
        return f"{self.household.name} - {self.ingredient.name}: {self.get_status_display()}"

class Menu(models.Model):
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="menus"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Menu for {self.household.name} ({self.created_at.date()})"


class MenuMeal(models.Model):
    STATE_CHOICES = [
        ("planned", "Planned"),
        ("done", "Done"),
        ("rejected", "Rejected"),
    ]

    MEAL_TYPE_CHOICES = [
        (1, "Breakfast"),
        (2, "Lunch"),
        (3, "Dinner"),
    ]

    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="menu_meals")
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name="menu_entries")
    state = models.CharField(
        max_length=10,
        choices=STATE_CHOICES,
        default="planned"
    )
    state_updated_at = models.DateTimeField(auto_now=True)

    # New fields
    day_number = models.PositiveIntegerField(
        help_text="Day index relative to menu start (1,2,3...)"
    )
    meal_type = models.PositiveSmallIntegerField(
        choices=MEAL_TYPE_CHOICES,
        default=3  # Dinner as default
    )

    class Meta:
        constraints = [
            # prevent duplicates: only one recipe per day_number + meal_type
            models.UniqueConstraint(
                fields=["menu", "day_number", "meal_type"],
                name="unique_meal_per_day_and_slot"
            ),
            # avoid duplicates of the same meal in the same menu
            models.UniqueConstraint(
                fields=["menu", "meal"],
                name="unique_meal_per_menu"
            ),
        ]

    def __str__(self):
        return f"Day {self.day_number} {self.get_meal_type_display()} - {self.meal.name} ({self.get_state_display()})"
