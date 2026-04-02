from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .richtext import sanitize_richtext


class DepartmentContentBase(models.Model):
    title = models.CharField(max_length=255)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)ss",
    )
    date_posted = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to="content/images/", blank=True, null=True)

    class Meta:
        abstract = True
        ordering = ["-date_posted"]

    def clean(self):
        super().clean()

        if self.posted_by and self.posted_by.role == "department_admin":
            if self.posted_by.department_id != self.department_id:
                raise ValidationError(
                    {"posted_by": "Department admins can only post content for their assigned department."}
                )


class Announcement(DepartmentContentBase):
    content = models.TextField()

    class Meta(DepartmentContentBase.Meta):
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"

    def __str__(self) -> str:
        return self.title


class News(DepartmentContentBase):
    content = models.TextField()

    class Meta(DepartmentContentBase.Meta):
        verbose_name = "News"
        verbose_name_plural = "News"

    def clean(self):
        super().clean()
        self.content = sanitize_richtext(self.content)

    def save(self, *args, **kwargs):
        self.content = sanitize_richtext(self.content)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class Event(DepartmentContentBase):
    description = models.TextField()
    event_date = models.DateTimeField()
    location = models.CharField(max_length=255)

    class Meta(DepartmentContentBase.Meta):
        verbose_name = "Event"
        verbose_name_plural = "Events"
        ordering = ["event_date", "-date_posted"]

    def __str__(self) -> str:
        return self.title
