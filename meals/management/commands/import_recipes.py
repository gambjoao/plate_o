import csv
import os
from django.core.management.base import BaseCommand
from django.db import transaction
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
        errors = 0

        try:
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=',')
                
                with transaction.atomic():
                    # Delete all existing meals
                    deleted_count = Meal.objects.all().count()
                    Meal.objects.all().delete()
                    self.stdout.write(self.style.WARNING(f'Deleted {deleted_count} existing meals.'))
                    
                    for idx, row in enumerate(reader, start=1):
                        try:
                            # Validate required fields
                            if not row.get('name'):
                                self.stderr.write(self.style.WARNING(f'Row {idx}: Missing name, skipping'))
                                errors += 1
                                continue

                            # Parse boolean value
                            overnight_prep = row.get('overnight_prep?', '').strip().lower() in ['true', '1', 'yes']

                            meal = Meal(
                                id=int(row['id']),
                                name=row['name'],
                                description=row.get('description', ''),
                                instructions=row.get('instructions', ''),
                                serves=int(row['serves']),
                                overnight_prep=overnight_prep,
                                time=int(row['time']),
                                nuisance_factor=float(row['nuisance_factor']),
                            )
                            meal.save(force_insert=True)
                            created += 1

                            # Progress feedback every 10 rows
                            if idx % 10 == 0:
                                self.stdout.write(f'Processed {idx} rows...')

                        except (ValueError, KeyError) as e:
                            self.stderr.write(self.style.ERROR(f'Row {idx}: Error processing row - {str(e)}'))
                            errors += 1
                            continue

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Fatal error: {str(e)}'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'Import complete: {created} created, {errors} errors.'
        ))