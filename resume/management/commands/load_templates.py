import os
from django.core.management.base import BaseCommand
from django.conf import settings
from resume.models import Template

class Command(BaseCommand):
    help = "Load HTML templates from disk into the Template model"

    def handle(self, *args, **options):
        templates_map = [
            {"name": "Classic Chronological",     "filename": "template1.html"},
            {"name": "Modern Minimalist",         "filename": "template2.html"},
            {"name": "Functional/Skills-Based",   "filename": "template3.html"},
            {"name": "Simple One-Column",         "filename": "template4.html"},
            {"name": "Hybrid",                    "filename": "template5.html"},
            {"name": "Professional Premium",      "filename": "template6.html"}
        ]

        repo_path = os.path.join(settings.BASE_DIR, 'resume', 'templates', 'resume', 'templates_repo')
        
        for item in templates_map:
            file_path = os.path.join(repo_path, item["filename"])
            if not os.path.exists(file_path):
                self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                tpl, created = Template.objects.get_or_create(
                    name=item["name"],
                    defaults={'content': html_content}
                )
                
                if not created:
                    tpl.content = html_content
                    tpl.save()

                status = "Created" if created else "Updated"
                self.stdout.write(self.style.SUCCESS(f"{status} template: {item['name']}"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {item['name']}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("Template loading completed!"))