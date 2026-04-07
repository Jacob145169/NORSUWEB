from django.db import models
import re


class Program(models.Model):
    program_code = models.CharField(max_length=30)
    program_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
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
