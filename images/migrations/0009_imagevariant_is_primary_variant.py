# Generated by Django 5.2 on 2025-05-04 13:36

from django.db import migrations, models


def set_primary_variants(apps, schema_editor):
    Image = apps.get_model("images", "Image")

    for image in Image.objects.all():
        image.imagevariant_set.filter(
            is_full_size=True,
            file_type__in=["jpg", "png"],
            gaussian_blur=0,
            brightness=1,
        ).update(is_primary_variant=True)


class Migration(migrations.Migration):

    dependencies = [
        ("images", "0008_imagevariant_regenerate"),
    ]

    operations = [
        migrations.AddField(
            model_name="imagevariant",
            name="is_primary_variant",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(set_primary_variants),
    ]
