from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0002_department_fields_schoolinfo"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="assistant_dean_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="department",
            name="dean_name",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
