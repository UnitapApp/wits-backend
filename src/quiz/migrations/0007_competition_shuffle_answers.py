# Generated by Django 5.0 on 2024-08-29 11:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0006_remove_usercompetition_is_hint_used_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='competition',
            name='shuffle_answers',
            field=models.BooleanField(default=False),
        ),
    ]