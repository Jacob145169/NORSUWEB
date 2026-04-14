import django.db.models.deletion
from django.db import migrations, models


def copy_legacy_program_uniform_images(apps, schema_editor):
    Program = apps.get_model("academics", "Program")
    ProgramUniformImage = apps.get_model("academics", "ProgramUniformImage")

    for program in Program.objects.exclude(course_uniform_image="").exclude(course_uniform_image__isnull=True):
        ProgramUniformImage.objects.create(
            program_id=program.pk,
            image=program.course_uniform_image.name,
            sort_order=0,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0002_program_course_uniform_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProgramUniformImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="programs/uniforms/")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("program", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="uniform_images", to="academics.program")),
            ],
            options={
                "verbose_name": "Program Uniform Image",
                "verbose_name_plural": "Program Uniform Images",
                "ordering": ["sort_order", "created_at", "pk"],
            },
        ),
        migrations.RunPython(copy_legacy_program_uniform_images, migrations.RunPython.noop),
    ]
