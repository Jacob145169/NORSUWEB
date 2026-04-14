from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0012_department_mission_vision"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolinfo",
            name="landing_background_image",
            field=models.ImageField(blank=True, null=True, upload_to="school_info/landing/"),
        ),
    ]
