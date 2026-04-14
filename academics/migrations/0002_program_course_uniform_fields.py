from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="program",
            name="course_uniform_description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="program",
            name="course_uniform_image",
            field=models.ImageField(blank=True, null=True, upload_to="programs/uniforms/"),
        ),
    ]
