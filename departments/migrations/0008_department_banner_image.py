from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0007_schoolinfo_department_banner_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="banner_image",
            field=models.ImageField(blank=True, null=True, upload_to="departments/banners/"),
        ),
    ]
