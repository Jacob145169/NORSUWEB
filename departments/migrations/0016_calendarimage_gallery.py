from django.db import migrations, models


def migrate_single_calendar_images_to_gallery(apps, schema_editor):
    SchoolInfo = apps.get_model("departments", "SchoolInfo")
    CalendarImage = apps.get_model("departments", "CalendarImage")

    for school_info in SchoolInfo.objects.exclude(calendar_image="").exclude(calendar_image__isnull=True):
        image_name = school_info.calendar_image.name
        if not image_name:
            continue

        if CalendarImage.objects.filter(school_info_id=school_info.pk, image=image_name).exists():
            continue

        CalendarImage.objects.create(
            school_info_id=school_info.pk,
            image=image_name,
        )


def restore_first_calendar_image_to_school_info(apps, schema_editor):
    SchoolInfo = apps.get_model("departments", "SchoolInfo")
    CalendarImage = apps.get_model("departments", "CalendarImage")

    for school_info in SchoolInfo.objects.all():
        first_calendar_image = CalendarImage.objects.filter(school_info_id=school_info.pk).order_by("created_at", "pk").first()
        if not first_calendar_image:
            continue

        school_info.calendar_image = first_calendar_image.image.name
        school_info.save(update_fields=["calendar_image"])


class Migration(migrations.Migration):

    dependencies = [
        ("departments", "0015_schoolinfo_calendar_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="CalendarImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="school_info/calendar/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "school_info",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="calendar_images", to="departments.schoolinfo"),
                ),
            ],
            options={
                "verbose_name": "Calendar Image",
                "verbose_name_plural": "Calendar Images",
                "ordering": ["created_at", "pk"],
            },
        ),
        migrations.RunPython(
            migrate_single_calendar_images_to_gallery,
            restore_first_calendar_image_to_school_info,
        ),
        migrations.RemoveField(
            model_name="schoolinfo",
            name="calendar_image",
        ),
    ]
