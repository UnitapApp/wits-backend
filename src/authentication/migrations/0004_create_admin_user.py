# Generated by Django 5.0 on 2024-08-26 10:02

from django.db import migrations


def create_super_user(apps, schema_editor):
    User = apps.get_model("auth", "User")
    User.objects.create_superuser("admin", "maktabi876@gmail.com", "ChangeSoon1234")


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0003_delete_apiuserprofile_userprofile_user"),
    ]

    operations = [
        migrations.RunPython(create_super_user, reverse_code=migrations.RunPython.noop),
    ]
