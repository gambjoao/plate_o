import os
import re
import unicodedata
from django.core.management.base import BaseCommand
from django.conf import settings
from meals.models import Meal

class Command(BaseCommand):
    help = "Link meal images to Meal objects if matching files exist in media/meal_images/"

    def normalize_filename(self, name):
        # Lowercase
        name = name.lower()

        # Remove anything inside parentheses and the parentheses
        name = name.replace('(', '').replace(')', '')

        # Strip accents
        name = ''.join(
            c for c in unicodedata.normalize('NFKD', name)
            if not unicodedata.combining(c)
        )

        # Replace spaces with underscores
        name = name.replace(' ', '_')

        # Remove extra non-alphanumeric characters (except underscores)
        name = re.sub(r'[^a-z0-9_]', '', name)

        return name.strip()

    def handle(self, *args, **options):
        images_path = os.path.join(settings.MEDIA_ROOT, 'meal_images')

        if not os.path.exists(images_path):
            self.stdout.write(self.style.WARNING(f"Directory not found: {images_path}"))
            return

        updated = 0
        missing = 0
        possible_extensions = ['.png', '.jpg', '.jpeg', '.webp']

        for meal in Meal.objects.all():
            normalized = self.normalize_filename(meal.name)

            found = False
            for ext in possible_extensions:
                filename = f"{normalized}{ext}"
                file_path = os.path.join(images_path, filename)

                if os.path.exists(file_path):
                    meal.image = f"meal_images/{filename}"
                    meal.save()
                    self.stdout.write(self.style.SUCCESS(f"Linked {filename} to {meal.name}"))
                    updated += 1
                    found = True
                    break

            if not found:
                self.stdout.write(f"No image for {meal.name}")
                missing += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone! {updated} linked, {missing} missing."))
