# Generated by Django 5.0 on 2024-08-15 12:23

import core.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='competition',
            old_name='sponsor',
            new_name='sponsors',
        ),
        migrations.RemoveField(
            model_name='competition',
            name='image_url',
        ),
        migrations.RemoveField(
            model_name='competition',
            name='token_image_url',
        ),
        migrations.AddField(
            model_name='competition',
            name='image',
            field=core.fields.CloudflareImagesField(blank=True, null=True, upload_to='', variant='public'),
        ),
        migrations.AddField(
            model_name='competition',
            name='token_image',
            field=core.fields.CloudflareImagesField(blank=True, null=True, upload_to='', variant='public'),
        ),
    ]