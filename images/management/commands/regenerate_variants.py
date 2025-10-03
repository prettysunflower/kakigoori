import logging
from io import BytesIO

from django.core.management.base import BaseCommand

from images.models import Image
from images.tasks import send_image_to_worker
from images.utils import get_b2_resource

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--images", nargs="+", type=str, required=False)

    def handle(self, *args, **options):
        if options["images"] and len(options["images"]) > 0:
            images_list = Image.objects.filter(id__in=options["images"])
        else:
            images_list = Image.objects.all()

        bucket = get_b2_resource()

        for image in images_list:
            image_downloaded = []

            for variant in image.imagevariant_set.all():
                print(f"Processing variant {variant.id}")

                if variant.is_full_size and (
                    variant.file_type == "jpg" or variant.file_type == "png"
                ):
                    print("Can't regenerate original image")
                    continue

                if variant.file_type == "webp" or variant.file_type == "avif":
                    if (
                        variant.parent_variant_for_optimized_versions.id
                        in image_downloaded
                    ):
                        image_data = image_downloaded[
                            variant.parent_variant_for_optimized_versions.id
                        ]
                    else:
                        image_data = BytesIO()
                        bucket.download_fileobj(
                            variant.parent_variant_for_optimized_versions.s3_filepath,
                            image_data,
                        )
                        image_downloaded[
                            variant.parent_variant_for_optimized_versions.id
                        ] = image_data

                    image_data.seek(0)
                    send_image_to_worker(image_variant=variant, image_data=image_data)
                    continue

                image, file_extension = variant.image.create_resized_image(
                    variant.height,
                    variant.width,
                    variant.gaussian_blur,
                    variant.brightness,
                )

                if file_extension == "jpg":
                    content_type = "image/jpeg"
                elif file_extension == "png":
                    content_type = "image/png"
                else:
                    content_type = "binary/octet-stream"

                variant.file_type = file_extension

                bucket.upload_fileobj(
                    image,
                    variant.s3_filepath,
                    ExtraArgs={"ContentType": content_type},
                )
