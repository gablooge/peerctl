# Generated by Django 3.2.14 on 2023-06-09 07:34

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_peerctl", "0038_auto_20230609_1125"),
    ]

    operations = [
        migrations.AddField(
            model_name="devicetemplate",
            name="default",
            field=models.BooleanField(default=False),
        ),
    ]
