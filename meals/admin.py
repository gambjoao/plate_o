from django import forms
from django.contrib import admin
from django.utils.html import format_html, format_html_join

from .models import (
    Ingredient,
    IngredientMeasure,
    IngredientNutritionToken,
    Meal,
    MealIngredient,
    NutritionToken,
)
from .services.token_calculator import compute_token_profile
from .services.recipe_import import normalize_meal_ingredient_fields, measure_exists


class IngredientMeasureInline(admin.TabularInline):
    model = IngredientMeasure
    extra = 1
    fields = ("unit_description", "multiplier")


class IngredientNutritionTokenInline(admin.TabularInline):
    model = IngredientNutritionToken
    extra = 1
    autocomplete_fields = ("token",)
    fields = ("token", "quantity")


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "base_unit", "portion_description")
    list_filter = ("base_unit",)
    search_fields = ("name",)
    inlines = [IngredientMeasureInline, IngredientNutritionTokenInline]


@admin.register(NutritionToken)
class NutritionTokenAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


class MealIngredientInlineForm(forms.ModelForm):
    class Meta:
        model = MealIngredient
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()

        # Skip validation on rows the user left empty / marked for deletion.
        if cleaned.get("DELETE") or not cleaned.get("ingredient"):
            return cleaned

        ingredient = cleaned["ingredient"]
        quantidade_desc, unit_desc, u_desc = normalize_meal_ingredient_fields(
            cleaned.get("u_quantity"),
            cleaned.get("u_desc"),
            cleaned.get("quantidade_desc"),
            cleaned.get("unit_desc"),
        )
        cleaned["u_desc"] = u_desc
        cleaned["quantidade_desc"] = quantidade_desc
        cleaned["unit_desc"] = unit_desc

        if u_desc and not measure_exists(ingredient, u_desc):
            self.add_error(
                "u_desc",
                f'"{ingredient.name}" has no conversion ratio for unit "{u_desc}" yet. '
                f"Add one on the ingredient's page first — otherwise this row is silently "
                f"left out of the token calculation.",
            )

        return cleaned


class MealIngredientInline(admin.TabularInline):
    model = MealIngredient
    form = MealIngredientInlineForm
    extra = 1
    autocomplete_fields = ("ingredient",)
    fields = (
        "ingredient",
        "u_quantity",
        "u_desc",
        "required",
        "quantidade_desc",
        "unit_desc",
        "sub",
        "notas",
    )


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ("name", "serves", "time", "nuisance_factor")
    search_fields = ("name",)
    inlines = [MealIngredientInline]
    readonly_fields = ("token_profile_display",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "description",
                    "serves",
                    "time",
                    "overnight_prep",
                    "nuisance_factor",
                    "image",
                )
            },
        ),
        ("Instructions", {"fields": ("instructions",)}),
        ("Token profile (computed)", {"fields": ("token_profile_display",)}),
    )

    def token_profile_display(self, obj):
        if not obj.pk:
            return "Save the recipe first to see its computed token profile."

        totals = compute_token_profile(obj)
        if not totals:
            return "No tokens computed — check that ingredients have measures and token values set."

        rows = format_html_join(
            "",
            "<tr><td style='padding-right:24px'>{}</td><td>{}</td></tr>",
            ((name, f"{value:.2f}") for name, value in sorted(totals.items())),
        )
        return format_html("<table>{}</table>", rows)

    token_profile_display.short_description = "Token totals"
