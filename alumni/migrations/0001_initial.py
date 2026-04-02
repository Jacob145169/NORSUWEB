import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("departments", "0002_department_fields_schoolinfo"),
    ]

    operations = [
        migrations.CreateModel(
            name="Alumni",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=255)),
                ("batch_year", models.PositiveIntegerField()),
                ("course_program", models.CharField(max_length=255)),
                ("photo", models.ImageField(blank=True, null=True, upload_to="alumni/photos/")),
                ("email", models.EmailField(help_text="Private alumni contact detail.", max_length=254)),
                ("contact_number", models.CharField(help_text="Private alumni contact detail.", max_length=30)),
                ("address", models.TextField(help_text="Private alumni contact detail.")),
                ("employment_status", models.CharField(blank=True, max_length=100)),
                ("company_name", models.CharField(blank=True, max_length=255)),
                ("job_title", models.CharField(blank=True, max_length=255)),
                ("is_public", models.BooleanField(default=False, help_text="Controls whether the alumni profile can be shown publicly.")),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alumni", to="departments.department")),
            ],
            options={
                "verbose_name": "Alumni",
                "verbose_name_plural": "Alumni",
                "ordering": ["-batch_year", "full_name"],
            },
        ),
    ]

