from django.core.management.base import BaseCommand
from projects.services import auto_complete_expired_projects


class Command(BaseCommand):
    help = "Checks and automatically completes/deactivates in-progress projects whose estimated completion date has passed."

    def handle(self, *args, **options):
        count = auto_complete_expired_projects()
        if count > 0:
            self.stdout.write(self.style.SUCCESS(f"Processed expired projects: {count} project(s) marked Completed and deactivated."))
        else:
            self.stdout.write("No expired projects required completion at this time.")
