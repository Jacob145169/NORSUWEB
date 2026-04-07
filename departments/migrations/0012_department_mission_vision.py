from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0011_schoolinfo_quality_policy"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="mission",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="department",
            name="vision",
            field=models.TextField(blank=True, default=""),
        ),
    ]
