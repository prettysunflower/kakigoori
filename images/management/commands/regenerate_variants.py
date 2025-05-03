from django.core.management.base import BaseCommand

from images.models import ImageVariant
from images.utils import get_b2_resource


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("variants", nargs="+", type=str)

    def handle(self, *args, **options):
        if options["variants"] and len(options["variants"]) > 0:
            variants = options["variants"]
        else:
            variants = ImageVariant.objects.all()

        bucket = get_b2_resource()

        for variant_id in variants:
            print("Regenerating variant %s" % variant_id)

            image_variant = ImageVariant.objects.filter(id=variant_id).first()

            if image_variant.is_full_size and (
                image_variant.file_type == "jpg" or image_variant.file_type == "png"
            ):
                print("Can't regenerate original image")
                continue

            if image_variant.file_type == "webp" or image_variant.file_type == "avif":
                image_variant.regenerate = True
                image_variant.save()
                continue

            image, file_extension = image_variant.image.create_resized_image(
                image_variant.height,
                image_variant.width,
                image_variant.gaussian_blur,
                image_variant.brightness,
            )

            if file_extension == "jpg":
                content_type = "image/jpeg"
            elif file_extension == "png":
                content_type = "image/png"
            else:
                content_type = "binary/octet-stream"

            image_variant.file_type = file_extension

            bucket.upload_fileobj(
                image,
                image_variant.backblaze_filepath,
                ExtraArgs={"ContentType": content_type},
            )
