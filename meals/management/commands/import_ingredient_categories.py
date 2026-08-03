import csv
import os
from django.core.management.base import BaseCommand
from meals.models import Ingredient, IngredientCategory


class Command(BaseCommand):
    help = (
        "Assign ingredient categories from a CSV with columns 'ingredient_id' and "
        "'category_path' (e.g. \"Frescos >> Peixes >> Peixes Frescos\"). Creates any "
        "missing IngredientCategory rows along the chain and points the ingredient "
        "at the leaf category."
    )

    def handle(self, *args, **kwargs):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_path = os.path.join(base_dir, 'data', 'ingredient_categories.csv')

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f'CSV file not found at: {csv_path}'))
            return

        updated = 0

        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:
                try:
                    ingredient = Ingredient.objects.get(pk=int(row.get('ingredient_id', '').strip()))
                except (Ingredient.DoesNotExist, ValueError, TypeError) as e:
                    self.stderr.write(self.style.WARNING(f"Skipping row with invalid ingredient: {row} ({e})"))
                    continue

                names = [n.strip() for n in row.get('category_path', '').split('>>') if n.strip()]
                if not names:
                    self.stderr.write(self.style.WARNING(f"Skipping row with empty category_path: {row}"))
                    continue

                category = None
                for name in names:
                    category, _ = IngredientCategory.objects.get_or_create(name=name, parent=category)

                ingredient.category = category
                ingredient.save(update_fields=['category'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Assigned categories to {updated} ingredients.'))
