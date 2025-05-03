import uuid
from io import BytesIO

from botocore.compat import file_type
from django.db import models
from django.utils import timezone

from images.utils import get_b2_resource
from PIL import Image as PILImage, ImageOps, ImageEnhance, ImageFilter


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creation_date = models.DateTimeField(default=timezone.now)
    uploaded = models.BooleanField(default=False)
    original_name = models.CharField(max_length=150)
    original_mime_type = models.CharField(max_length=10)
    original_md5 = models.CharField(max_length=32)
    is_webp_available = models.BooleanField(default=False)
    is_avif_available = models.BooleanField(default=False)
    is_jpegli_available = models.BooleanField(default=False)
    model_version = models.IntegerField(default=1)
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

    def create_variant_tasks(self, variant):
        ImageVariant(
            image=variant.image,
            height=variant.height,
            width=variant.width,
            is_full_size=variant.is_full_size,
            file_type="avif",
            gaussian_blur=variant.gaussian_blur,
            brightness=variant.brightness,
            available=False,
        ).save()

        ImageVariant(
            image=variant.image,
            height=variant.height,
            width=variant.width,
            is_full_size=variant.is_full_size,
            file_type="webp",
            gaussian_blur=variant.gaussian_blur,
            brightness=variant.brightness,
            available=False,
        ).save()

    def download_original_variant(self):
        bucket = get_b2_resource()

        original_image = BytesIO()
        original_variant = self.imagevariant_set.filter(
            is_full_size=True,
            file_type__in=["jpg", "png"],
            gaussian_blur=0,
            brightness=1,
        ).first()

        bucket.download_fileobj(
            original_variant.backblaze_filepath,
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

        bucket.upload_fileobj(
            resized_image,
            image_variant.backblaze_filepath,
            ExtraArgs={"ContentType": content_type},
        )

        image_variant.save()

        self.create_variant_tasks(image_variant)

        return image_variant


class ImageVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    height = models.IntegerField()
    width = models.IntegerField()
    gaussian_blur = models.FloatField(default=0)
    brightness = models.FloatField(default=1)
    is_full_size = models.BooleanField(default=False)
    file_type = models.CharField(max_length=10)
    available = models.BooleanField(default=False)
    regenerate = models.BooleanField(default=False)

    @property
    def backblaze_filepath(self):
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


class ImageVariantTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    height = models.IntegerField()
    width = models.IntegerField()
    gaussian_blur = models.FloatField(default=0)
    brightness = models.FloatField(default=1)
    original_file_type = models.CharField(max_length=10)
    file_type = models.CharField(max_length=10)


class AuthorizationKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    can_upload_image = models.BooleanField(default=False)
    can_upload_variant = models.BooleanField(default=False)
