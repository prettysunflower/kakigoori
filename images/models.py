import uuid
from io import BytesIO

from django.db import models
from django.utils import timezone

from images.tasks import send_image_to_worker
from images.utils import get_b2_resource
from PIL import Image as PILImage, ImageOps, ImageEnhance, ImageFilter


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creation_date = models.DateTimeField(default=timezone.now)
    uploaded = models.BooleanField(default=False)
    original_name = models.CharField(max_length=150)
    original_mime_type = models.CharField(max_length=10)
    original_md5 = models.CharField(max_length=32)
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)
    version = models.IntegerField(default=2)

    @property
    def thumbnail_size(self):
        if self.height > self.width:
            return int(600 * self.width / self.height), 600
        else:
            return 600, int(600 * self.height / self.width)

    @property
    def backblaze_filepath(self):
        return f"{self.id.hex[:2]}/{self.id.hex[2:4]}/{self.id.hex}"

    def create_variant_tasks(self, variant, image_data: BytesIO):
        avif_variant = ImageVariant(
            image=variant.image,
            height=variant.height,
            width=variant.width,
            is_full_size=variant.is_full_size,
            file_type="avif",
            gaussian_blur=variant.gaussian_blur,
            brightness=variant.brightness,
            available=False,
        )

        avif_variant.save()

        webp_variant = ImageVariant(
            image=variant.image,
            height=variant.height,
            width=variant.width,
            is_full_size=variant.is_full_size,
            file_type="webp",
            gaussian_blur=variant.gaussian_blur,
            brightness=variant.brightness,
            available=False,
        )
        webp_variant.save()

        send_image_to_worker(image_variant=avif_variant, image_data=image_data)
        send_image_to_worker(image_variant=webp_variant, image_data=image_data)

    def download_original_variant(self):
        bucket = get_b2_resource()

        original_image = BytesIO()
        original_variant = self.imagevariant_set.filter(is_primary_variant=True).first()

        bucket.download_fileobj(
            original_variant.s3_filepath,
            original_image,
        )
        original_image.seek(0)
        return original_image

    def create_resized_image(
        self,
        height,
        width,
        gaussian_blur,
        brightness,
    ):
        original_image = self.download_original_variant()
        resized_image = BytesIO()
        file_extension = "jpg"

        with PILImage.open(original_image) as im:
            ImageOps.exif_transpose(im, in_place=True)
            im = im.filter(ImageFilter.GaussianBlur(gaussian_blur))
            enhancer = ImageEnhance.Brightness(im)
            im = enhancer.enhance(brightness)
            im.thumbnail(
                (width, height), resample=PILImage.Resampling.LANCZOS, reducing_gap=3.0
            )

            if im.has_transparency_data:
                try:
                    im.save(resized_image, "PNG", quality=90)
                    file_extension = "png"
                except OSError:
                    im.convert("RGB").save(resized_image, "JPEG", quality=90)
            else:
                try:
                    im.save(resized_image, "JPEG", quality=90)
                except OSError:
                    im.convert("RGB").save(resized_image, "JPEG", quality=90)

        resized_image.seek(0)

        return resized_image, file_extension

    def create_variant(self, width, height, gaussian_blur, brightness):
        bucket = get_b2_resource()

        image_variant = ImageVariant(
            image=self,
            height=height,
            width=width,
            is_full_size=False,
            file_type="jpg",
            gaussian_blur=gaussian_blur,
            brightness=brightness,
            available=True,
        )

        resized_image, file_extension = self.create_resized_image(
            height, width, gaussian_blur, brightness
        )

        if file_extension == "jpg":
            content_type = "image/jpeg"
        elif file_extension == "png":
            content_type = "image/png"
        else:
            content_type = "binary/octet-stream"

        image_variant.file_type = file_extension

        # We're making a copy here because we had errors that the next seek was failing because resized_image
        # was closed.
        s3_copy = BytesIO(resized_image.read())

        bucket.upload_fileobj(
            s3_copy,
            image_variant.s3_filepath,
            ExtraArgs={"ContentType": content_type},
        )

        image_variant.save()

        resized_image.seek(0)

        self.create_variant_tasks(image_variant, image_data=resized_image)

        return image_variant


class ImageVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    height = models.IntegerField()
    width = models.IntegerField()
    gaussian_blur = models.FloatField(default=0)
    brightness = models.FloatField(default=1)
    is_primary_variant = models.BooleanField(default=False)
    is_full_size = models.BooleanField(default=False)
    file_type = models.CharField(max_length=10)
    available = models.BooleanField(default=False)

    @property
    def s3_filepath(self):
        return f"{self.id.hex[:2]}/{self.id.hex[2:4]}/{self.id.hex}.{self.file_type}"

    @property
    def parent_variant_for_optimized_versions(self):
        return ImageVariant.objects.filter(
            image_id=self.image_id,
            height=self.height,
            width=self.width,
            gaussian_blur=self.gaussian_blur,
            brightness=self.brightness,
            file_type__in=["jpg", "png"],
        ).first()


class AuthorizationKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    can_upload_image = models.BooleanField(default=False)
    can_upload_variant = models.BooleanField(default=False)
