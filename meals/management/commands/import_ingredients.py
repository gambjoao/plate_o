from django.core.management.base import BaseCommand
from django.db import connection
from meals.models import Ingredient, NutritionToken, IngredientNutritionToken
import os
import csv

class Command(BaseCommand):
    help = 'Import ingredients and token data from CSV into DB'

    def handle(self, *args, **kwargs):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_path = os.path.join(base_dir, 'data', 'ingredientes.csv')

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f'CSV file not found at: {csv_path}'))
            return

        Ingredient.objects.all().delete()
        IngredientNutritionToken.objects.all().delete()

        with connection.cursor() as cursor:
            cursor.execute("ALTER SEQUENCE meals_ingredient_id_seq RESTART WITH 1;")
            cursor.execute("ALTER SEQUENCE meals_ingredientnutritiontoken_id_seq RESTART WITH 1;")

        token_column_map = {
            'red meat tokens': 'red meat',
            'white meat tokens': 'white meat',
            'fish tokens': 'fish',
            'seafish tokens': 'seafood',
            'veggies tokens': 'veggies',
            'legumes tokens': 'legumes',
        }

        # Get NutritionToken objects into a lookup dict
        token_objects = {
            token.name: token for token in NutritionToken.objects.all()
        }

        created = 0
        token_links = 0

        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:
                name = row.get('ing_desc', '').strip()
                base_unit = row.get('Unidade sugerida', '').strip().lower()
                portion_desc = row.get('Porção', '').strip()

                if not name:
                    continue

                if base_unit not in {'g', 'ml', 'u'}:
                    self.stderr.write(self.style.WARNING(
                        f'Unknown base unit "{base_unit}" for ingredient "{name}". Defaulting to "g".'
                    ))
                    base_unit = 'g'

                ingredient = Ingredient.objects.create(
                    name=name,
                    base_unit=base_unit,
                    portion_description=portion_desc if portion_desc else None
                )
                created += 1

                # Now handle token values
                for col_name, token_name in token_column_map.items():
                    val = row.get(col_name, '').strip()
                    if not val:
                        continue
                    try:
                        quantity = float(val)
                    except ValueError:
                        continue
                    if quantity == 0:
                        continue

                    token_obj = token_objects.get(token_name)
                    if not token_obj:
                        self.stderr.write(self.style.WARNING(
                            f'Token "{token_name}" not found in DB. Skipping.'
                        ))
                        continue

                    IngredientNutritionToken.objects.create(
                        ingredient=ingredient,
                        token=token_obj,
                        quantity=quantity
                    )
                    token_links += 1

        self.stdout.write(self.style.SUCCESS(f'Imported {created} ingredients with {token_links} token links.'))
