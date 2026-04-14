from django.core.validators import FileExtensionValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0006_content_publication_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="announcement",
            name="video",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="content/videos/",
                validators=[FileExtensionValidator(allowed_extensions=["mp4", "webm", "ogg", "mov", "m4v"])],
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="video",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="content/videos/",
                validators=[FileExtensionValidator(allowed_extensions=["mp4", "webm", "ogg", "mov", "m4v"])],
            ),
        ),
        migrations.AddField(
            model_name="news",
            name="video",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="content/videos/",
                validators=[FileExtensionValidator(allowed_extensions=["mp4", "webm", "ogg", "mov", "m4v"])],
            ),
        ),
    ]
