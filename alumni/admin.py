from django.contrib import admin

from .models import Alumni


@admin.register(Alumni)
class AlumniAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "batch_year",
        "course_program",
        "department",
        "employment_status",
        "is_public",
    )
    list_filter = ("department", "batch_year", "is_public", "employment_status")
    search_fields = ("full_name", "course_program", "company_name", "job_title")

