import re
from types import SimpleNamespace

from django.db import models


class Program(models.Model):
    program_code = models.CharField(max_length=30)
    program_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    course_uniform_description = models.TextField(blank=True, default="")
    course_uniform_image = models.ImageField(upload_to="programs/uniforms/", blank=True, null=True)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        related_name="programs",
    )

    class Meta:
        ordering = ["program_name"]
        verbose_name = "Program"
        verbose_name_plural = "Programs"
        constraints = [
            models.UniqueConstraint(
                fields=["department", "program_code"],
                name="academics_unique_program_code_per_department",
            )
        ]

    def __str__(self) -> str:
        return f"{self.program_code} - {self.program_name}"

    @property
    def display_name(self) -> str:
        code = (self.program_code or "").strip()
        name = (self.program_name or "").strip()
        if not code or not name:
            return name

        pattern = rf"^{re.escape(code)}\s*[-:]\s*"
        if re.match(pattern, name, flags=re.IGNORECASE):
            return re.sub(pattern, "", name, count=1, flags=re.IGNORECASE).strip()

        if name.casefold() == code.casefold():
            return name

        return name

    @property
    def uniform_images_for_display(self):
        prefetched_uniform_images = getattr(self, "prefetched_uniform_images", None)
        uniform_images = list(prefetched_uniform_images if prefetched_uniform_images is not None else self.uniform_images.all())
        if uniform_images:
            return uniform_images
        if self.course_uniform_image:
            return [
                SimpleNamespace(
                    pk=f"legacy-{self.pk}",
                    image=self.course_uniform_image,
                    is_legacy=True,
                )
            ]
        return []


class ProgramUniformImage(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="uniform_images",
    )
    image = models.ImageField(upload_to="programs/uniforms/")
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "created_at", "pk"]
        verbose_name = "Program Uniform Image"
        verbose_name_plural = "Program Uniform Images"

    def __str__(self) -> str:
        return f"{self.program.program_code} Uniform {self.pk}"


class Instructor(models.Model):
    full_name = models.CharField(max_length=255)
    photo = models.ImageField(upload_to="instructors/photos/", blank=True, null=True)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        related_name="instructors",
    )

    class Meta:
        ordering = ["full_name"]
        verbose_name = "Instructor"
        verbose_name_plural = "Instructors"

    def __str__(self) -> str:
        return self.full_name
