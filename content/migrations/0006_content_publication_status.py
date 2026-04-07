from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0005_event_end_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="announcement",
            name="publication_status",
            field=models.CharField(
                choices=[("draft", "Draft"), ("published", "Published")],
                db_index=True,
                default="published",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="publication_status",
            field=models.CharField(
                choices=[("draft", "Draft"), ("published", "Published")],
                db_index=True,
                default="published",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="news",
            name="publication_status",
            field=models.CharField(
                choices=[("draft", "Draft"), ("published", "Published")],
                db_index=True,
                default="published",
                max_length=16,
            ),
        ),
    ]
