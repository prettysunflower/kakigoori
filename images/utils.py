import subprocess

import boto3
from botocore.config import Config
from django.conf import settings


def get_b2_resource():
    b2 = boto3.resource(
        service_name="s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_KEY_ID,
        aws_secret_access_key=settings.S3_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )

    bucket = b2.Bucket(settings.S3_BUCKET)

    return bucket


def remove_exif_gps_data(image_data: bytes) -> bytes:
    result = subprocess.run(
        ["exiftool", "-gps:all=", "-"], input=image_data, capture_output=True
    )

    if not result.check_returncode():
        return image_data
    else:
        raise Exception(result.stderr)
