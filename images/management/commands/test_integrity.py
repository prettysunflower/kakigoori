from django.core.management.base import BaseCommand

from images.models import Image
from images.utils import get_b2_resource
import botocore


class Command(BaseCommand):
    bucket = None

    def __init__(self):
        self.bucket = get_b2_resource()
        super(Command, self).__init__()

    def test_image_has_variants(self):
        return Image.objects.filter(imagevariant=None).all()

    def test_primary_variant_every_image_has_only_one(self):
        images_with_problems = []

        for image in Image.objects.all():
            image_variant_set = image.imagevariant_set.filter(is_primary_variant=True)
            if image_variant_set.count() > 1:
                found_etags = []
                for image_variant in image_variant_set.all():
                    try:
                        e_tag = self.bucket.Object(
                            image_variant.backblaze_filepath
                        ).e_tag[1:-1]
                    except botocore.exceptions.ClientError as e:
                        if e.response["Error"]["Code"] == "404":
                            print(f"Variant {image_variant.id} not found, deleting...")
                            image_variant.delete()
                            continue
                        else:
                            raise

                    if e_tag in found_etags:
                        image_variant.delete()
                    else:
                        found_etags.append(e_tag)

                if len(found_etags) > 1:
                    images_with_problems.append(image.id)
                else:
                    print(
                        f"SELF-HEALED: Image {image.id} had multiple primary variants, but all of them were identical. We only kept the first one, and deleted the others"
                    )

        return images_with_problems

    def test_every_image_has_primary_variant(self):
        images_with_problems = []

        for image in Image.objects.all():
            if image.imagevariant_set.filter(is_primary_variant=True).count() == 0:
                images_with_problems.append(image)

        return images_with_problems

    def handle(self, *args, **options):
        print("Testing integrity")

        print("Testing that all images have variants")

        problems = self.test_image_has_variants()

        if problems:
            print(f"FAIL, the following images don't have any variants:")
            for problem in problems:
                print(f"- {problem.id}")

            print("Self-healing...")

            for problem in problems:
                problem.delete()

            print("Done")
        else:
            print("OK")

        print("Testing if every image has only one primary variant...")

        problems = self.test_primary_variant_every_image_has_only_one()

        if problems:
            print(f"FAIL")
            for problem in problems:
                print(f"Image {problem.id} has the following variants:")
                for variant in problem.imagevariant_set.filter(
                    is_primary_variant=True
                ).all():
                    print(f"- {variant.id}")
        else:
            print("OK")

        print("Testing if every image has at least one primary variant...")

        problems = self.test_every_image_has_primary_variant()
        if problems:
            print(f"FAIL, the following images don't have any primary variants:")
            for problem in problems:
                print(f"- {problem.id}")

        else:
            print("OK")
