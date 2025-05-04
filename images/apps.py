from django.apps import AppConfig
from django.db.models.signals import post_delete
from django.dispatch import receiver
from images.utils import get_b2_resource


@receiver(post_delete)
def delete_image_from_s3_if_variant_is_deleted(sender, instance, **kwargs):
    bucket = get_b2_resource()
    bucket.delete_objects(Delete={"Objects": [{"Key": instance.backblaze_filepath}]})


class ImagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "images"
