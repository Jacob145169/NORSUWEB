from django.db import migrations, models


DEPARTMENT_GRADIENTS = {
    "CAS": "#2563eb",
    "CTED": "#f59e0b",
    "CCJE": "#d97706",
    "CBA": "#facc15",
    "CIT": "#0ea5e9",
    "CAF": "#84cc16",
}


def seed_department_gradient_colors(apps, schema_editor):
    Department = apps.get_model("departments", "Department")

    for code, gradient_end in DEPARTMENT_GRADIENTS.items():
        Department.objects.filter(code=code, theme_color_secondary="").update(
            theme_color_secondary=gradient_end
        )


def clear_seeded_department_gradient_colors(apps, schema_editor):
    Department = apps.get_model("departments", "Department")

    for code, gradient_end in DEPARTMENT_GRADIENTS.items():
        Department.objects.filter(code=code, theme_color_secondary=gradient_end).update(
            theme_color_secondary=""
        )


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0013_schoolinfo_landing_background_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="theme_color_secondary",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Optional second hex color used for department gradients.",
                max_length=7,
            ),
        ),
        migrations.RunPython(
            seed_department_gradient_colors,
            clear_seeded_department_gradient_colors,
        ),
    ]
