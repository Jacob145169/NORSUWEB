from django.db import migrations, models


def seed_calendar_image_sort_order(apps, schema_editor):
    CalendarImage = apps.get_model("departments", "CalendarImage")
    SchoolInfo = apps.get_model("departments", "SchoolInfo")

    for school_info in SchoolInfo.objects.all():
        for index, calendar_image in enumerate(
            CalendarImage.objects.filter(school_info_id=school_info.pk).order_by("created_at", "pk")
        ):
            calendar_image.sort_order = index
            calendar_image.save(update_fields=["sort_order"])


class Migration(migrations.Migration):

    dependencies = [
        ("departments", "0016_calendarimage_gallery"),
    ]

    operations = [
        migrations.AddField(
            model_name="calendarimage",
            name="sort_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(seed_calendar_image_sort_order, migrations.RunPython.noop),
    ]
