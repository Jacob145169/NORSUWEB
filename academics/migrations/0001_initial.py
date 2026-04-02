import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("departments", "0002_department_fields_schoolinfo"),
    ]

    operations = [
        migrations.CreateModel(
            name="Instructor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=255)),
                ("photo", models.ImageField(blank=True, null=True, upload_to="instructors/photos/")),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="instructors", to="departments.department")),
            ],
            options={
                "verbose_name": "Instructor",
                "verbose_name_plural": "Instructors",
                "ordering": ["full_name"],
            },
        ),
        migrations.CreateModel(
            name="Program",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("program_code", models.CharField(max_length=30)),
                ("program_name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="programs", to="departments.department")),
            ],
            options={
                "verbose_name": "Program",
                "verbose_name_plural": "Programs",
                "ordering": ["program_name"],
                "constraints": [
                    models.UniqueConstraint(fields=("department", "program_code"), name="academics_unique_program_code_per_department"),
                ],
            },
        ),
    ]
