import base64
import json
from io import BytesIO

import pika

from images.utils import get_b2_resource
from kakigoori import settings


def send_image_to_worker(image_variant, image_data: BytesIO | None = None):
    original_image_variant = image_variant.parent_variant_for_optimized_versions

    if image_data:
        file = image_data
    else:
        s3_bucket = get_b2_resource()

        file = BytesIO()
        s3_bucket.download_fileobj(original_image_variant.s3_filepath, file)

    file.seek(0)

    message = {
        "variant_id": str(image_variant.id),
        "original_file": base64.b64encode(file.getbuffer()).decode("utf-8"),
    }

    connection = pika.BlockingConnection(settings.RABBITMQ_CONNECTION_PARAMETERS)
    channel = connection.channel()

    if image_variant.file_type == "avif":
        queue = "kakigoori_avif"
    elif image_variant.file_type == "webp":
        queue = "kakigoori_webp"
    else:
        return

    channel.queue_declare(queue=queue, durable=True)

    channel.basic_publish(
        exchange="",
        routing_key=queue,
        body=json.dumps(message).encode("utf-8"),
        properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
    )

    connection.close()
