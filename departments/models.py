from django.db import models
from django.utils.text import slugify


class Department(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    description = models.TextField(blank=True)
    mission = models.TextField(blank=True, default="")
    vision = models.TextField(blank=True, default="")
    banner_image = models.ImageField(upload_to="departments/banners/", blank=True, null=True)
    dean_name = models.CharField(max_length=255, blank=True)
    assistant_dean_name = models.CharField(max_length=255, blank=True)
    dean_photo = models.ImageField(upload_to="departments/leadership/", blank=True, null=True)
    assistant_dean_photo = models.ImageField(upload_to="departments/leadership/", blank=True, null=True)
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
    strategic_goals = models.TextField(blank=True, default="")
    core_values = models.TextField(blank=True, default="")
    quality_policy = models.TextField(blank=True, default="")
    history = models.TextField()
    history_image = models.ImageField(upload_to="school_info/history/", blank=True, null=True)

    class Meta:
        verbose_name = "School Information"
        verbose_name_plural = "School Information"

    @classmethod
    def get_solo(cls):
        school_info = cls.objects.filter(pk=1).first()
        if school_info is not None:
            return school_info

        school_info = cls.objects.order_by("pk").first()
        if school_info is not None:
            return school_info

        school_info, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "college_name": "Negros Oriental State University",
                "mission": "",
                "vision": "",
                "strategic_goals": "",
                "core_values": "",
                "quality_policy": "",
                "history": "",
                "history_image": None,
            },
        )
        return school_info

    @property
    def core_value_cards(self):
        raw_value = (self.core_values or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not raw_value:
            return []

        blocks = [block.strip() for block in raw_value.split("\n\n") if block.strip()]
        cards = []

        for index, block in enumerate(blocks):
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if not lines:
                continue

            title = lines[0]
            description = " ".join(lines[1:]).strip()
            initial = next((char.upper() for char in title if char.isalnum()), "")
            icon_key = "star"
            normalized_title = title.lower()

            if "spirit" in normalized_title:
                icon_key = "lotus"
            elif "honest" in normalized_title or "integr" in normalized_title:
                icon_key = "shield"
            elif "innov" in normalized_title or "creat" in normalized_title:
                icon_key = "bulb"
            elif "nurt" in normalized_title or "care" in normalized_title or "compassion" in normalized_title:
                icon_key = "hands"
            elif "excel" in normalized_title or "quality" in normalized_title:
                icon_key = "star"

            cards.append(
                {
                    "title": title,
                    "description": description,
                    "initial": initial,
                    "icon_key": icon_key,
                    "accent_index": index % 5,
                }
            )

        return cards

    @property
    def core_values_wordmark(self):
        return "".join(card["initial"] for card in self.core_value_cards if card["initial"])

    def __str__(self) -> str:
        return self.college_name
