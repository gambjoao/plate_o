import csv
import os
from django.core.management.base import BaseCommand
from meals.models import Meal

class Command(BaseCommand):
    help = 'Import recipes from a hardcoded CSV file into the Recipe model'

    def handle(self, *args, **kwargs):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_path = os.path.join(base_dir, 'data', 'receitas.csv')

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f'CSV file not found at: {csv_path}'))
            return

        created = 0
        with open(csv_path, newline='', encoding='iso-8859-1') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')  # Set semicolon delimiter
            for row in reader:
                Meal.objects.create(
                    name=row['name'],
                    description=row['description'],
                    instructions=row['instructions'],
                    serves=int(row['serves']),
                    overnight_prep=row['overnight_prep?'].strip().lower() in ['true', '1', 'yes'],
                    time=int(row['time']),
                    nuisance_factor=float(row['nuisance_factor']),
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {created} recipes.'))
