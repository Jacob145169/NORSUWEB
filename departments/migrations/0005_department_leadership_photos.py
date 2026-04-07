from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0004_alter_department_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="assistant_dean_photo",
            field=models.ImageField(blank=True, null=True, upload_to="departments/leadership/"),
        ),
        migrations.AddField(
            model_name="department",
            name="dean_photo",
            field=models.ImageField(blank=True, null=True, upload_to="departments/leadership/"),
        ),
    ]
