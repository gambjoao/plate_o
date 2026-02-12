import csv
import os
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from meals.models import Meal

class Command(BaseCommand):
    help = 'Import recipes from a hardcoded CSV file into the Recipe model'

    def parse_instructions(self, instructions_text):
        """
        Parse instructions from '1 - text || 2 - text || ...' format
        into JSON array: [{"step": 1, "instruction": "text"}, ...]
        """
        if not instructions_text or instructions_text.strip() == '':
            return []
        
        # Split by ||
        steps = instructions_text.split('||')
        parsed_instructions = []
        
        for step_text in steps:
            step_text = step_text.strip()
            if not step_text:
                continue
            
            # Match pattern: "number - instruction text"
            # Using regex to extract step number and instruction
            match = re.match(r'^(\d+)\s*-\s*(.+)$', step_text)
            
            if match:
                step_num = int(match.group(1))
                instruction = match.group(2).strip()
                parsed_instructions.append({
                    "step": step_num,
                    "instruction": instruction
                })
            else:
                # If format doesn't match, log warning but continue
                self.stderr.write(self.style.WARNING(
                    f'Could not parse step format: "{step_text[:50]}..."'
                ))
        
        return parsed_instructions

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

                            # Parse instructions from text to JSON
                            instructions_json = self.parse_instructions(row.get('instructions', ''))

                            meal = Meal(
                                id=int(row['id']),
                                name=row['name'],
                                description=row.get('description', ''),
                                instructions=instructions_json,  # Now a list of dicts
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