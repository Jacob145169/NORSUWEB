from django.db import migrations


def clear_legacy_program_uniform_images(apps, schema_editor):
    Program = apps.get_model("academics", "Program")
    Program.objects.filter(course_uniform_image__isnull=False).exclude(course_uniform_image="").update(course_uniform_image=None)


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0003_program_uniform_image_gallery"),
    ]

    operations = [
        migrations.RunPython(clear_legacy_program_uniform_images, migrations.RunPython.noop),
    ]
