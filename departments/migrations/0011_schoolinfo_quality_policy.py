from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0010_schoolinfo_strategic_goals_core_values"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolinfo",
            name="quality_policy",
            field=models.TextField(blank=True, default=""),
        ),
    ]
