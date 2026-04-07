from django.db import models


class Alumni(models.Model):
    full_name = models.CharField(max_length=255)
    id_number = models.CharField(max_length=50, blank=True, default="")
    batch_year = models.PositiveIntegerField()
    course_program = models.CharField(max_length=255)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        related_name="alumni",
    )
    photo = models.ImageField(upload_to="alumni/photos/", blank=True, null=True)
    email = models.EmailField(help_text="Private alumni contact detail.")
    contact_number = models.CharField(max_length=30, help_text="Private alumni contact detail.")
    address = models.TextField(help_text="Private alumni contact detail.")
    employment_status = models.CharField(max_length=100, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    job_title = models.CharField(max_length=255, blank=True)
    is_public = models.BooleanField(
        default=False,
        help_text="Controls whether the alumni profile can be shown publicly.",
    )

    class Meta:
        ordering = ["-batch_year", "full_name"]
        verbose_name = "Alumni"
        verbose_name_plural = "Alumni"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.batch_year})"
