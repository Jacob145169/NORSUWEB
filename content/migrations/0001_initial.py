import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("departments", "0002_department_fields_schoolinfo"),
    ]

    operations = [
        migrations.CreateModel(
            name="Announcement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("date_posted", models.DateTimeField(auto_now_add=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="content/images/")),
                ("content", models.TextField()),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="announcements", to="departments.department")),
                ("posted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="announcements", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Announcement",
                "verbose_name_plural": "Announcements",
                "ordering": ["-date_posted"],
            },
        ),
        migrations.CreateModel(
            name="Event",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("date_posted", models.DateTimeField(auto_now_add=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="content/images/")),
                ("description", models.TextField()),
                ("event_date", models.DateTimeField()),
                ("location", models.CharField(max_length=255)),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="departments.department")),
                ("posted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="events", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Event",
                "verbose_name_plural": "Events",
                "ordering": ["event_date", "-date_posted"],
            },
        ),
        migrations.CreateModel(
            name="News",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("date_posted", models.DateTimeField(auto_now_add=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="content/images/")),
                ("content", models.TextField()),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="news", to="departments.department")),
                ("posted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="news", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "News",
                "verbose_name_plural": "News",
                "ordering": ["-date_posted"],
            },
        ),
    ]

