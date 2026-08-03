from django.db import models

class IngredientCategory(models.Model):
    """Self-referential so the pantry can group ingredients into an
    arbitrary-depth aisle/category tree (e.g. Frescos > Peixes > Peixes
    Frescos) instead of the backend hardcoding fixed level names."""

    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='children',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name_plural = 'Ingredient categories'
        unique_together = ('name', 'parent')

    def __str__(self):
        return ' >> '.join(self.path_names())

    def path_names(self):
        """Category names from root to this node, e.g. ['Frescos', 'Peixes']."""
        names = []
        node = self
        while node is not None:
            names.append(node.name)
            node = node.parent
        return list(reversed(names))


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
    category = models.ForeignKey(
        IngredientCategory,
        null=True,
        blank=True,
        related_name='ingredients',
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return self.name


class Tag(models.Model):
    CATEGORY_CHOICES = [
        ('country', 'Country'),
        ('region', 'Region'),
        ('diet', 'Diet'),
        ('spice_level', 'Spice level'),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class Meal(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    instructions = models.JSONField(default=list)
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
    tags = models.ManyToManyField(
        Tag,
        related_name='meals',
        blank=True,
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
    number_of_members = models.PositiveIntegerField(default=2)

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
    portions_multiplier = models.PositiveIntegerField(
        default=1,
        help_text="How many times this meal's yield was doubled/tripled to cover the household for this slot"
    )

    class Meta:
        constraints = [
            # prevent duplicates: only one recipe per day_number + meal_type
            models.UniqueConstraint(
                fields=["menu", "day_number", "meal_type"],
                name="unique_meal_per_day_and_slot"
            ),
            # NOTE: the same meal can now appear in multiple slots within a menu
            # (leftovers covering more than one occasion), so there is no longer
            # a uniqueness constraint on (menu, meal).
        ]

    def __str__(self):
        return f"Day {self.day_number} {self.get_meal_type_display()} - {self.meal.name} ({self.get_state_display()})"


class MenuFreezeEntry(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="freeze_entries")
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    portions = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.menu} - freeze {self.portions}x {self.meal.name}"
