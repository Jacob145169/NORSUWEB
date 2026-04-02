from django.core.management.base import BaseCommand
from django.db import transaction

from academics.models import Program
from departments.models import Department
from departments.seed_data import DEPARTMENTS, PROGRAMS_BY_DEPARTMENT


class Command(BaseCommand):
    help = "Seed the initial departments and programs for the website."

    @transaction.atomic
    def handle(self, *args, **options):
        seeded_departments = 0
        seeded_programs = 0

        for department_data in DEPARTMENTS:
            department, created = Department.objects.update_or_create(
                code=department_data["code"],
                defaults={
                    "name": department_data["name"],
                    "description": department_data["description"],
                    "theme_color": department_data["theme_color"],
                    "is_active": True,
                },
            )

            if created:
                seeded_departments += 1
                self.stdout.write(self.style.SUCCESS(f"Created department: {department.code}"))
            else:
                self.stdout.write(self.style.WARNING(f"Updated department: {department.code}"))

            for program_data in PROGRAMS_BY_DEPARTMENT.get(department.code, []):
                program, program_created = Program.objects.update_or_create(
                    department=department,
                    program_code=program_data["program_code"],
                    defaults={
                        "program_name": program_data["program_name"],
                        "description": "",
                    },
                )

                if program_created:
                    seeded_programs += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  Created program: {program.program_code} - {program.program_name}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  Updated program: {program.program_code} - {program.program_name}")
                    )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Departments created: {seeded_departments}"))
        self.stdout.write(self.style.SUCCESS(f"Programs created: {seeded_programs}"))
        self.stdout.write(self.style.SUCCESS("Initial seed completed successfully."))
