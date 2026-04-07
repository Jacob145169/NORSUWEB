from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0004_make_events_department_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="end_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
