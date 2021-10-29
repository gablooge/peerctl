# Generated by Django 3.2.7 on 2021-10-19 07:57

import django.core.validators
import django_inet.models
import netfields.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("django_peerctl", "0004_auto_20211015_0948"),
    ]

    operations = [
        migrations.AddField(
            model_name="physicalport",
            name="mac_address",
            field=netfields.fields.MACAddressField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="network",
            name="asn",
            field=django_inet.models.ASNField(
                db_index=True,
                unique=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MinValueValidator(0),
                ],
            ),
        ),
    ]
