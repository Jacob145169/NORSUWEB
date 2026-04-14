from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("departments", "0017_calendarimage_sort_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="course_uniform_description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="department",
            name="course_uniform_image",
            field=models.ImageField(blank=True, null=True, upload_to="departments/uniforms/"),
        ),
    ]
