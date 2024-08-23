# Generated by Django 5.0 on 2024-08-15 12:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
        ('quiz', '0002_rename_sponsor_competition_sponsors_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='competition',
            name='user_profile',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='authentication.apiuserprofile'),
        ),
    ]