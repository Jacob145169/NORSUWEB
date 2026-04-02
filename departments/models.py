from django.db import models
from django.utils.text import slugify


class Department(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="departments/logos/", blank=True, null=True)
    theme_color = models.CharField(max_length=7, default="#0f6b4f", help_text="Hex color code, e.g. #0f6b4f.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class SchoolInfo(models.Model):
    college_name = models.CharField(max_length=255)
    mission = models.TextField()
    vision = models.TextField()
    history = models.TextField()

    class Meta:
        verbose_name = "School Information"
        verbose_name_plural = "School Information"

    def __str__(self) -> str:
        return self.college_name
