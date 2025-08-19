import csv
import os
from django.core.management.base import BaseCommand
from meals.models import Meal, Ingredient, MealIngredient

class Command(BaseCommand):
    help = 'Import meal-ingredient relationships with metadata from CSV'

    def handle(self, *args, **kwargs):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_path = os.path.join(base_dir, 'data', 'receitas_ingredientes.csv')

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f'CSV file not found at: {csv_path}'))
            return

        created = 0
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    meal_id = int(row['meal_id'])
                    ingredient_id = int(row['ingredient_id'])
                    meal = Meal.objects.get(id=meal_id)
                    ingredient = Ingredient.objects.get(id=ingredient_id)

                    MealIngredient.objects.create(
                        meal=meal,
                        ingredient=ingredient,
                        quantidade_desc=row.get('quantidade_desc', '').strip(),
                        unit_desc=row.get('unit_desc', '').strip(),
                        u_quantity=row.get('u_quantity', '').strip(),
                        u_desc=row.get('u_desc', '').strip(),
                        sub=row.get('Sub', '').strip(),
                        notas=row.get('Notas', '').strip(),
                        required=row.get('Required', '1').strip() == '1'
                    )
                    created += 1

                except Meal.DoesNotExist:
                    self.stderr.write(f"Meal with ID {meal_id} not found.")
                except Ingredient.DoesNotExist:
                    self.stderr.write(f"Ingredient with ID {ingredient_id} not found.")
                except Exception as e:
                    self.stderr.write(f"Error importing row: {e}")

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {created} meal-ingredient links.'))
