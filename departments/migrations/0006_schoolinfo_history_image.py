from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0005_department_leadership_photos"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolinfo",
            name="history_image",
            field=models.ImageField(blank=True, null=True, upload_to="school_info/history/"),
        ),
    ]
