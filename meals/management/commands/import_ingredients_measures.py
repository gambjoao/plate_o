import csv
import os
from django.core.management.base import BaseCommand
from django.db import connection
from meals.models import IngredientMeasure

class Command(BaseCommand):
    help = 'Import ingredient measurement conversions from CSV into the IngredientMeasure model'

    def handle(self, *args, **kwargs):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_path = os.path.join(base_dir, 'data', 'ingredients_measures.csv')

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f'CSV file not found at: {csv_path}'))
            return

        # Clear existing data
        IngredientMeasure.objects.all().delete()


        valid_units = {'c', 'u', 'tbsp', 'tsp', 'g', 'ml', 'qb'}
        created = 0

        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:
                try:
                    ingredient_id = int(row.get('ingredient_id', '').strip())
                    unit_description = row.get('u_desc', '').strip().lower()
                    multiplier = float(row.get('multiplier', '').strip())
                except (ValueError, TypeError) as e:
                    self.stderr.write(self.style.WARNING(f"Skipping row with invalid data: {row} ({e})"))
                    continue

                if unit_description not in valid_units:
                    self.stderr.write(self.style.WARNING(
                        f'Skipping invalid unit "{unit_description}" for ingredient ID {ingredient_id}'
                    ))
                    continue

                IngredientMeasure.objects.create(
                    ingredient_id=ingredient_id,
                    unit_description=unit_description,
                    multiplier=multiplier
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {created} ingredient measures.'))
