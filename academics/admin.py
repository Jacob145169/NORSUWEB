from django.contrib import admin

from .models import Instructor, Program


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("program_code", "program_name", "department")
    list_filter = ("department",)
    search_fields = ("program_code", "program_name")


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "department")
    list_filter = ("department",)
    search_fields = ("full_name",)

