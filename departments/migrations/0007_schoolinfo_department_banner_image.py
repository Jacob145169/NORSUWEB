from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0006_schoolinfo_history_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolinfo",
            name="department_banner_image",
            field=models.ImageField(blank=True, null=True, upload_to="school_info/department_banner/"),
        ),
    ]
