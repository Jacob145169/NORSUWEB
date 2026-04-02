from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="code",
            field=models.CharField(default="TEMP", max_length=20, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="department",
            name="logo",
            field=models.ImageField(blank=True, null=True, upload_to="departments/logos/"),
        ),
        migrations.AddField(
            model_name="department",
            name="theme_color",
            field=models.CharField(default="#0f6b4f", help_text="Hex color code, e.g. #0f6b4f.", max_length=7),
        ),
        migrations.CreateModel(
            name="SchoolInfo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("college_name", models.CharField(max_length=255)),
                ("mission", models.TextField()),
                ("vision", models.TextField()),
                ("history", models.TextField()),
            ],
            options={
                "verbose_name": "School Information",
                "verbose_name_plural": "School Information",
            },
        ),
    ]
