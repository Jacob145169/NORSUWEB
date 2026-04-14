from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("departments", "0014_department_theme_color_secondary"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolinfo",
            name="calendar_image",
            field=models.ImageField(blank=True, null=True, upload_to="school_info/calendar/"),
        ),
    ]
