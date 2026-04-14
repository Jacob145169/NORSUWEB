from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import formats, timezone

from .richtext import sanitize_richtext


ALLOWED_VIDEO_EXTENSIONS = ["mp4", "webm", "ogg", "mov", "m4v"]


class PublicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"


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
    publication_status = models.CharField(
        max_length=16,
        choices=PublicationStatus.choices,
        default=PublicationStatus.PUBLISHED,
        db_index=True,
    )
    image = models.ImageField(upload_to="content/images/", blank=True, null=True)
    video = models.FileField(
        upload_to="content/videos/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_VIDEO_EXTENSIONS)],
    )

    class Meta:
        abstract = True
        ordering = ["-date_posted"]

    @property
    def source_label(self):
        if self.department_id and self.department:
            return self.department.name
        return "University"

    @property
    def is_draft(self):
        return self.publication_status == PublicationStatus.DRAFT

    def clean(self):
        super().clean()

        if self.posted_by and self.posted_by.role == "department_admin":
            if self.department_id is None:
                raise ValidationError(
                    {"department": "Department admins can only post content for their assigned department."}
                )
            if self.posted_by.department_id != self.department_id:
                raise ValidationError(
                    {"posted_by": "Department admins can only post content for their assigned department."}
                )


class Announcement(DepartmentContentBase):
    content = models.TextField()
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        null=True,
        blank=True,
    )

    class Meta(DepartmentContentBase.Meta):
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"

    def clean(self):
        super().clean()
        self.content = sanitize_richtext(self.content)

    def save(self, *args, **kwargs):
        self.content = sanitize_richtext(self.content)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class News(DepartmentContentBase):
    content = models.TextField()
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        null=True,
        blank=True,
    )

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
    end_date = models.DateTimeField(blank=True, null=True)
    location = models.CharField(max_length=255)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        null=True,
        blank=True,
    )

    class Meta(DepartmentContentBase.Meta):
        verbose_name = "Event"
        verbose_name_plural = "Events"
        ordering = ["event_date", "-date_posted"]

    @staticmethod
    def _display_datetime(value):
        if value is None:
            return ""
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return f"{formats.date_format(value, 'M d, Y')} | {formats.date_format(value, 'g:i A')}"

    @property
    def schedule_label(self):
        if self.end_date is None:
            return self._display_datetime(self.event_date)

        start = timezone.localtime(self.event_date) if timezone.is_aware(self.event_date) else self.event_date
        end = timezone.localtime(self.end_date) if timezone.is_aware(self.end_date) else self.end_date

        if end <= start:
            return self._display_datetime(start)

        if start.date() == end.date():
            return (
                f"{formats.date_format(start, 'M d, Y')} | "
                f"{formats.date_format(start, 'g:i A')} - {formats.date_format(end, 'g:i A')}"
            )

        return f"{self._display_datetime(start)} - {self._display_datetime(end)}"

    def clean(self):
        super().clean()
        self.description = sanitize_richtext(self.description)

        if self.end_date and self.event_date and self.end_date < self.event_date:
            raise ValidationError({"end_date": "End date must be later than the event start date."})

    def save(self, *args, **kwargs):
        self.description = sanitize_richtext(self.description)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title
