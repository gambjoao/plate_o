import os
import re
import unicodedata
from django.core.management.base import BaseCommand
from django.conf import settings
from meals.models import Ingredient

class Command(BaseCommand):
    help = "Link ingredient images to Ingredient objects if matching files exist in media/ingredient_icons/"

    def normalize_filename(self, name):
        # Lowercase
        name = name.lower()

        # Remove anything inside parentheses and the parentheses
        name = name.replace('(', '').replace(')', '')

        
        # Strip accents (ã -> a, ç -> c, etc.)
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
        icons_path = os.path.join(settings.MEDIA_ROOT, 'ingredient_icons')

        if not os.path.exists(icons_path):
            self.stdout.write(self.style.WARNING(f"Directory not found: {icons_path}"))
            return

        updated = 0
        missing = 0
        possible_extensions = ['.png', '.jpg', '.jpeg', '.webp']

        for ingredient in Ingredient.objects.all():
            normalized = self.normalize_filename(ingredient.name)

            found = False
            for ext in possible_extensions:
                filename = f"{normalized}{ext}"
                file_path = os.path.join(icons_path, filename)

                if os.path.exists(file_path):
                    ingredient.icon = f"ingredient_icons/{filename}"
                    ingredient.save()
                    self.stdout.write(self.style.SUCCESS(f"Linked {filename} to {ingredient.name}"))
                    updated += 1
                    found = True
                    break

            if not found:
                self.stdout.write(f"No image for {ingredient.name}")
                missing += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone! {updated} linked, {missing} missing."))
