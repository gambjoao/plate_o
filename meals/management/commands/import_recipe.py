import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from meals.models import (
    Ingredient,
    IngredientMeasure,
    IngredientNutritionToken,
    Meal,
    MealIngredient,
    NutritionToken,
    Tag,
)
from meals.services.recipe_import import measure_exists, normalize_meal_ingredient_fields
from meals.services.token_calculator import compute_token_profile


class Command(BaseCommand):
    help = (
        "Import a single recipe from a JSON payload, creating any missing "
        "ingredients/unit-measures/token values along the way. See the "
        "add-recipe skill for the expected JSON schema."
    )

    def add_arguments(self, parser):
        parser.add_argument("json_path", help="Path to a JSON file matching the recipe import schema.")

    def handle(self, *args, **options):
        with open(options["json_path"], encoding="utf-8") as f:
            payload = json.load(f)

        try:
            meal_data = payload["meal"]
            ingredients_data = payload["ingredients"]
            name = meal_data["name"]
            serves = meal_data["serves"]
            time = meal_data["time"]
            nuisance_factor = meal_data["nuisance_factor"]
        except KeyError as e:
            raise CommandError(f"Payload is missing required field: {e}")

        tags_data = payload.get("tags", [])
        valid_categories = {choice[0] for choice in Tag.CATEGORY_CHOICES}
        for tag_item in tags_data:
            if tag_item.get("category") not in valid_categories:
                raise CommandError(
                    f'Tag "{tag_item.get("name")}" has missing/invalid "category" '
                    f'(must be one of {sorted(valid_categories)}).'
                )

        if Meal.objects.filter(name__iexact=name).exists():
            raise CommandError(
                f'A meal named "{name}" already exists. Refusing to import a duplicate — '
                f"rename it, or remove/update the existing one manually first."
            )

        report = {
            "new_ingredients": [],
            "reused_ingredients": [],
            "new_measures": [],
            "new_tokens": [],
            "new_tags": [],
        }

        with transaction.atomic():
            ingredients_by_name = {}

            for item in ingredients_data:
                ing_name = item["name"].strip()
                ingredient = Ingredient.objects.filter(name__iexact=ing_name).first()

                if ingredient is None:
                    base_unit = item.get("base_unit")
                    if base_unit not in ("g", "ml", "u"):
                        raise CommandError(
                            f'Ingredient "{ing_name}" is new but "base_unit" is missing or invalid '
                            f'(must be "g", "ml", or "u").'
                        )

                    ingredient = Ingredient.objects.create(
                        name=ing_name,
                        base_unit=base_unit,
                        portion_description=item.get("portion_description") or None,
                    )
                    report["new_ingredients"].append(ing_name)

                    for token_name, quantity in (item.get("tokens") or {}).items():
                        token = NutritionToken.objects.filter(name__iexact=token_name).first()
                        if token is None:
                            existing = ", ".join(NutritionToken.objects.values_list("name", flat=True))
                            raise CommandError(
                                f'Unknown nutrition token "{token_name}" for ingredient "{ing_name}". '
                                f"Existing tokens: {existing}"
                            )
                        IngredientNutritionToken.objects.create(
                            ingredient=ingredient, token=token, quantity=quantity
                        )
                        report["new_tokens"].append(f"{ing_name} -> {token.name}: {quantity}")
                else:
                    report["reused_ingredients"].append(ing_name)

                for measure in item.get("measures") or []:
                    u_desc = measure["unit_desc"].strip().lower()
                    if not measure_exists(ingredient, u_desc):
                        IngredientMeasure.objects.create(
                            ingredient=ingredient,
                            unit_description=u_desc,
                            multiplier=measure["multiplier"],
                        )
                        report["new_measures"].append(f"{ing_name} -> {u_desc}: {measure['multiplier']}")

                ingredients_by_name[ing_name.lower()] = ingredient

            meal = Meal.objects.create(
                name=name,
                description=meal_data.get("description", ""),
                instructions=meal_data.get("instructions", []),
                serves=serves,
                overnight_prep=meal_data.get("overnight_prep", False),
                time=time,
                nuisance_factor=nuisance_factor,
            )

            tag_objects = []
            for tag_item in tags_data:
                tag_name = tag_item["name"].strip()
                tag = Tag.objects.filter(name__iexact=tag_name).first()
                if tag is None:
                    tag = Tag.objects.create(name=tag_name, category=tag_item["category"])
                    report["new_tags"].append(f"{tag_name} ({tag_item['category']})")
                tag_objects.append(tag)
            if tag_objects:
                meal.tags.set(tag_objects)

            for item in ingredients_data:
                ing_name = item["name"].strip()
                ingredient = ingredients_by_name[ing_name.lower()]

                try:
                    mi = item["meal_ingredient"]
                    u_quantity = mi["u_quantity"]
                    u_desc_raw = mi["u_desc"]
                except KeyError as e:
                    raise CommandError(f'Ingredient "{ing_name}" is missing meal_ingredient field: {e}')

                quantidade_desc, unit_desc, u_desc = normalize_meal_ingredient_fields(
                    u_quantity, u_desc_raw, mi.get("quantidade_desc"), mi.get("unit_desc")
                )

                if not measure_exists(ingredient, u_desc):
                    raise CommandError(
                        f'"{ing_name}" has no conversion ratio for unit "{u_desc}" — '
                        f'add one under "measures" for this ingredient in the payload.'
                    )

                MealIngredient.objects.create(
                    meal=meal,
                    ingredient=ingredient,
                    quantidade_desc=quantidade_desc,
                    unit_desc=unit_desc,
                    u_quantity=str(u_quantity),
                    u_desc=u_desc,
                    sub=mi.get("sub") or "",
                    notas=mi.get("notas") or "",
                    required=mi.get("required", True),
                )

        self.stdout.write(self.style.SUCCESS(f'Created meal "{meal.name}" (id={meal.pk}).'))

        if report["new_ingredients"]:
            self.stdout.write(self.style.WARNING("NEEDS REVIEW - new ingredients created:"))
            for n in report["new_ingredients"]:
                self.stdout.write(f"  - {n}")
        if report["new_tokens"]:
            self.stdout.write(self.style.WARNING("NEEDS REVIEW - new token values assigned:"))
            for n in report["new_tokens"]:
                self.stdout.write(f"  - {n}")
        if report["new_measures"]:
            self.stdout.write(self.style.WARNING("NEEDS REVIEW - new unit ratios created:"))
            for n in report["new_measures"]:
                self.stdout.write(f"  - {n}")
        if report["new_tags"]:
            self.stdout.write(self.style.WARNING("NEEDS REVIEW - new tags created:"))
            for n in report["new_tags"]:
                self.stdout.write(f"  - {n}")
        if report["reused_ingredients"]:
            self.stdout.write(f'Reused existing ingredients: {", ".join(report["reused_ingredients"])}')
        if tag_objects:
            self.stdout.write(f'Tags applied: {", ".join(t.name for t in tag_objects)}')

        totals = compute_token_profile(meal)
        self.stdout.write("Computed token profile for this recipe:")
        for token_name, value in sorted(totals.items()):
            self.stdout.write(f"  {token_name}: {value:.2f}")
