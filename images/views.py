import hashlib
import os
import random
import string
from io import BytesIO

from PIL import Image as PILImage
from PIL import JpegImagePlugin
from django.conf import settings
from django.http import (
    JsonResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
)
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from images.decorators import (
    get_image,
    can_upload_variant,
    can_upload_image,
)
from images.models import Image, ImageVariant
from images.utils import get_b2_resource, remove_exif_gps_data

JpegImagePlugin._getmp = lambda x: None


def index(request):
    return render(request, "index.html", {
        "DEBUG": settings.DEBUG,
    })


@csrf_exempt
@can_upload_image
def upload(request):
    file = request.FILES["file"]

    bucket = get_b2_resource()

    filename = file.name

    with PILImage.open(file) as im:
        height, width = (im.height, im.width)

        if im.format == "JPEG":
            file_extension = "jpg"
            content_type = "image/jpeg"
        elif im.format == "PNG":
            file_extension = "png"
            content_type = "image/png"
        else:
            new_file = BytesIO()
            filename = (
                "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
                + ".jpg"
            )
            im.save(
                new_file,
                format="jpeg",
                quality=95,
                icc_profile=im.info.get("icc_profile"),
                keep_rgb=True,
            )
            file = new_file
            content_type = "image/jpeg"
            file_extension = "jpg"

    file.seek(0)
    file_md5_hash = hashlib.file_digest(file, "md5").hexdigest()
    file.seek(0)

    same_md5_image = Image.objects.filter(original_md5=file_md5_hash).first()
    if same_md5_image:
        return JsonResponse({"created": False, "id": same_md5_image.id})

    image = Image(
        original_name=filename,
        original_mime_type=content_type,
        original_md5=file_md5_hash,
        height=height,
        width=width,
        version=3,
    )

    image.save()

    variant, _ = ImageVariant.objects.get_or_create(
        image=image,
        height=height,
        width=width,
        file_type=file_extension,
        is_full_size=True,
        available=True,
        is_primary_variant=True,
    )

    image_data = remove_exif_gps_data(file.read())

    bucket.put_object(
        Body=image_data,
        Key=variant.s3_filepath,
        ContentType=content_type,
    )

    image.create_variant_tasks(variant, BytesIO(image_data))
    image.uploaded = True
    image.save()

    return JsonResponse({"created": True, "id": image.id}, status=201)


def image_with_size(request, image, width, height, image_type):
    gaussian_blur = float(request.GET.get("gaussian_blur", 0))
    brightness = float(request.GET.get("brightness", 1))

    image_variants = ImageVariant.objects.filter(
        image=image,
        height=height,
        width=width,
        gaussian_blur=gaussian_blur,
        brightness=brightness,
        available=True,
    )
    if image_type != "auto":
        if image_type == "original":
            image_variants = image_variants.filter(file_type__in=["jpg", "png"])
        else:
            image_variants = image_variants.filter(file_type=image_type)

    variants = image_variants.all()

    if not variants:
        if image_type != "auto" and image_type != "original":
            return JsonResponse({"error": "Image version not available"}, status=404)
        else:
            image_variant = image.create_variant(
                width, height, gaussian_blur, brightness
            )

            return redirect(
                f"{settings.S3_PUBLIC_BASE_PATH}/{image_variant.s3_filepath}"
            )

    if image_type == "auto":
        variants_preferred_order = ["avif", "webp", "jpg", "png"]
    elif image_type == "original":
        variants_preferred_order = ["jpg", "png"]
    else:
        variants_preferred_order = [image_type]

    accept_header = request.headers.get("Accept", default="")

    for file_type in variants_preferred_order:
        if (
            file_type == "avif"
            and image_type == "auto"
            and "image/avif" not in accept_header
        ):
            continue

        if (
            file_type == "webp"
            and image_type == "auto"
            and "image/webp" not in accept_header
        ):
            continue

        variant = [x for x in image_variants if x.file_type == file_type]
        if not variant:
            continue

        variant = variant[0]

        return redirect(f"{settings.S3_PUBLIC_BASE_PATH}/{variant.s3_filepath}")

    return HttpResponseNotFound()


@get_image
def get_image_with_height(request, image, height, image_type):
    if height >= image.height:
        height = image.height
        width = image.width
    else:
        width = int(height * image.width / image.height)

    return image_with_size(request, image, width, height, image_type)


@get_image
def get_image_with_width(request, image, width, image_type):
    if width >= image.width:
        width = image.width
        height = image.height
    else:
        height = int(width * image.height / image.width)

    return image_with_size(request, image, width, height, image_type)


@get_image
def get(request, image, image_type):
    return image_with_size(request, image, image.width, image.height, image_type)


@get_image
def get_thumbnail(request, image, image_type):
    width, height = image.thumbnail_size

    return image_with_size(request, image, width, height, image_type)
