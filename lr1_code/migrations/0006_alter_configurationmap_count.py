# Generated by Django 5.1.1 on 2024-09-27 11:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lr1_code', '0005_configuration_plane_configurationmap_delete_plane'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configurationmap',
            name='count',
            field=models.IntegerField(),
        ),
    ]
