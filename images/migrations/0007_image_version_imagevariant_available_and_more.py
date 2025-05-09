# Generated by Django 5.1.1 on 2024-11-10 15:11

import uuid
from django.db import migrations, models


def fill_mymodel_uuid(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    ImageVariant = apps.get_model("images", "imagevariant")
    for obj in ImageVariant.objects.using(db_alias).all():
        obj.uuid = uuid.uuid4()
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ("images", "0006_imagevarianttask"),
    ]

    operations = [
        migrations.AddField(
            model_name="image",
            name="version",
            field=models.IntegerField(default=2),
        ),
        migrations.AddField(
            model_name="imagevariant",
            name="available",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="imagevariant",
            name="brightness",
            field=models.FloatField(default=1),
        ),
        migrations.AddField(
            model_name="imagevariant",
            name="gaussian_blur",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="imagevarianttask",
            name="brightness",
            field=models.FloatField(default=1),
        ),
        migrations.AddField(
            model_name="imagevarianttask",
            name="gaussian_blur",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="imagevariant",
            name="uuid",
            field=models.UUIDField(null=True),
        ),
        migrations.RunPython(fill_mymodel_uuid, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="imagevariant",
            name="uuid",
            field=models.UUIDField(
                default=uuid.uuid4, serialize=False, editable=False, unique=True
            ),
        ),
        migrations.RemoveField("imagevariant", "id"),
        migrations.RenameField(
            model_name="imagevariant", old_name="uuid", new_name="id"
        ),
        migrations.AlterField(
            model_name="imagevariant",
            name="id",
            field=models.UUIDField(
                primary_key=True, default=uuid.uuid4, serialize=False, editable=False
            ),
        ),
    ]
