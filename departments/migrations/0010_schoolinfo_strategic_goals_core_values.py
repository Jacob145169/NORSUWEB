from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0009_remove_schoolinfo_department_banner_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolinfo",
            name="core_values",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="schoolinfo",
            name="strategic_goals",
            field=models.TextField(blank=True, default=""),
        ),
    ]
