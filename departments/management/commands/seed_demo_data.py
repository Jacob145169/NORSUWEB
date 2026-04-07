from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from academics.models import Instructor, Program
from accounts.models import RoleChoices, User
from alumni.models import Alumni
from content.models import Announcement, Event, News
from departments.demo_seed_data import DEMO_CREDENTIALS, DEMO_DEPARTMENTS, DEMO_SCHOOL_INFO
from departments.models import Department, SchoolInfo


class Command(BaseCommand):
    help = "Seed realistic demo data for development and presentations."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding demo data..."))

        school_info, _ = SchoolInfo.objects.update_or_create(
            pk=1,
            defaults=DEMO_SCHOOL_INFO,
        )
        self.stdout.write(self.style.SUCCESS(f"School information ready: {school_info.college_name}"))

        super_admin = self._seed_super_admin()
        counts = {
            "departments": 0,
            "programs": 0,
            "instructors": 0,
            "announcements": 0,
            "news": 0,
            "events": 0,
            "alumni": 0,
            "department_admins": 0,
        }

        for department_data in DEMO_DEPARTMENTS:
            department, _ = Department.objects.update_or_create(
                code=department_data["code"],
                defaults={
                    "name": department_data["name"],
                    "description": department_data["description"],
                    "theme_color": department_data["theme_color"],
                    "is_active": True,
                },
            )
            counts["departments"] += 1

            department_admin = self._seed_department_admin(department, department_data["admin"])
            counts["department_admins"] += 1

            counts["programs"] += self._seed_programs(department, department_data["programs"])
            counts["instructors"] += self._seed_instructors(department, department_data["instructors"])
            counts["announcements"] += self._seed_announcements(department, department_admin, department_data["announcements"])
            counts["news"] += self._seed_news(department, department_admin, department_data["news"])
            counts["events"] += self._seed_events(department, department_admin, department_data["events"])
            counts["alumni"] += self._seed_alumni(department, department_data["alumni"])

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo data seeding completed successfully."))
        for label, value in counts.items():
            self.stdout.write(self.style.SUCCESS(f"{label.replace('_', ' ').title()}: {value}"))

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Demo credentials only. Do not use these passwords in production."))
        self.stdout.write(
            f"Super admin: {DEMO_CREDENTIALS['super_admin']['username']} / {DEMO_CREDENTIALS['super_admin']['password']}"
        )
        self.stdout.write(
            "Department admins: <department_code>_admin equivalents such as "
            f"cas_admin / {DEMO_CREDENTIALS['department_admin_password']}"
        )
        self.stdout.write(f"Content ownership defaulted to super admin account: {super_admin.username}")

    def _seed_super_admin(self):
        data = DEMO_CREDENTIALS["super_admin"]
        super_admin = User.objects.filter(role=RoleChoices.SUPER_ADMIN).first()
        created = False

        if super_admin is None:
            super_admin, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "full_name": data["full_name"],
                    "email": data["email"],
                    "role": RoleChoices.SUPER_ADMIN,
                    "is_active": True,
                    "is_staff": True,
                    "is_superuser": True,
                },
            )

        super_admin.full_name = data["full_name"]
        super_admin.username = data["username"]
        super_admin.email = data["email"]
        super_admin.role = RoleChoices.SUPER_ADMIN
        super_admin.department = None
        super_admin.is_active = True
        super_admin.is_staff = True
        super_admin.is_superuser = True
        super_admin.set_password(data["password"])
        super_admin.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created demo super admin: {super_admin.username}"))
        else:
            self.stdout.write(self.style.WARNING(f"Updated demo super admin: {super_admin.username}"))

        return super_admin

    def _seed_department_admin(self, department, admin_data):
        department_admin = User.objects.filter(
            role=RoleChoices.DEPARTMENT_ADMIN,
            department=department,
        ).first()
        created = False

        if department_admin is None:
            department_admin, created = User.objects.get_or_create(
                username=admin_data["username"],
                defaults={
                    "full_name": admin_data["full_name"],
                    "email": admin_data["email"],
                    "role": RoleChoices.DEPARTMENT_ADMIN,
                    "department": department,
                    "is_active": True,
                    "is_staff": True,
                },
            )

        department_admin.full_name = admin_data["full_name"]
        department_admin.username = admin_data["username"]
        department_admin.email = admin_data["email"]
        department_admin.role = RoleChoices.DEPARTMENT_ADMIN
        department_admin.department = department
        department_admin.is_active = True
        department_admin.is_staff = True
        department_admin.is_superuser = False
        department_admin.set_password(DEMO_CREDENTIALS["department_admin_password"])
        department_admin.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created department admin for {department.code}: {department_admin.username}"))
        else:
            self.stdout.write(self.style.WARNING(f"Updated department admin for {department.code}: {department_admin.username}"))

        return department_admin

    def _seed_programs(self, department, programs):
        count = 0
        for program_data in programs:
            Program.objects.update_or_create(
                department=department,
                program_code=program_data["program_code"],
                defaults={
                    "program_name": program_data["program_name"],
                    "description": program_data["description"],
                },
            )
            count += 1
        return count

    def _seed_instructors(self, department, instructors):
        count = 0
        for full_name in instructors:
            Instructor.objects.update_or_create(
                department=department,
                full_name=full_name,
                defaults={"photo": None},
            )
            count += 1
        return count

    def _seed_announcements(self, department, posted_by, announcements):
        count = 0
        for item in announcements:
            Announcement.objects.update_or_create(
                department=department,
                title=item["title"],
                defaults={
                    "content": item["content"],
                    "posted_by": posted_by,
                    "image": None,
                },
            )
            count += 1
        return count

    def _seed_news(self, department, posted_by, news_items):
        count = 0
        for item in news_items:
            News.objects.update_or_create(
                department=department,
                title=item["title"],
                defaults={
                    "content": item["content"],
                    "posted_by": posted_by,
                    "image": None,
                },
            )
            count += 1
        return count

    def _seed_events(self, department, posted_by, events):
        count = 0
        for item in events:
            event_date = timezone.make_aware(datetime.strptime(item["event_date"], "%Y-%m-%d %H:%M"))
            Event.objects.update_or_create(
                department=department,
                title=item["title"],
                defaults={
                    "description": item["description"],
                    "event_date": event_date,
                    "location": item["location"],
                    "posted_by": posted_by,
                    "image": None,
                },
            )
            count += 1
        return count

    def _seed_alumni(self, department, alumni_items):
        count = 0
        for item in alumni_items:
            Alumni.objects.update_or_create(
                department=department,
                full_name=item["full_name"],
                defaults={
                    "id_number": item.get("id_number", ""),
                    "batch_year": item["batch_year"],
                    "course_program": item["course_program"],
                    "photo": None,
                    "email": item["email"],
                    "contact_number": item["contact_number"],
                    "address": item["address"],
                    "employment_status": item["employment_status"],
                    "company_name": item["company_name"],
                    "job_title": item["job_title"],
                    "is_public": item["is_public"],
                },
            )
            count += 1
        return count
