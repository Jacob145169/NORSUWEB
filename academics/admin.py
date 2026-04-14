from django.contrib import admin

from .models import Instructor, Program, ProgramUniformImage


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("program_code", "program_name", "department", "uniform_image_count")
    list_filter = ("department",)
    search_fields = ("program_code", "program_name")

    @admin.display(description="Uniform Pictures")
    def uniform_image_count(self, obj):
        return obj.uniform_images.count() or (1 if obj.course_uniform_image else 0)


@admin.register(ProgramUniformImage)
class ProgramUniformImageAdmin(admin.ModelAdmin):
    list_display = ("program", "sort_order", "created_at")
    list_filter = ("program__department", "program")
    search_fields = ("program__program_code", "program__program_name")


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "department")
    list_filter = ("department",)
    search_fields = ("full_name",)
