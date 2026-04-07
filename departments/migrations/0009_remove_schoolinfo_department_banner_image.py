from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0008_department_banner_image"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="schoolinfo",
            name="department_banner_image",
        ),
    ]
