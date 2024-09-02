# Generated by Django 5.0 on 2024-08-28 07:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0005_alter_competition_amount_won_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usercompetition',
            name='is_hint_used',
        ),
        migrations.AddField(
            model_name='competition',
            name='hint_count',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='usercompetition',
            name='hint_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='usercompetition',
            name='tx_hash',
            field=models.CharField(blank=True, max_length=1000),
        ),
    ]