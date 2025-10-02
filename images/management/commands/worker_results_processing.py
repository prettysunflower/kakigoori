import base64
import json

import pika
from django.conf import settings
from django.core.management.base import BaseCommand
import logging

from images.models import ImageVariant
from images.utils import get_b2_resource

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        connection = pika.BlockingConnection(settings.rabbitmq_connection_parameters)

        channel = connection.channel()
        channel.queue_declare(queue="process_variant", durable=True)

        def callback(ch, method, properties, body):
            args = json.loads(body.decode("utf-8"))

            variant_file = base64.b64decode(args["variant_file"])
            variant_id = args["variant_id"]

            logger.info("Processing variant {}".format(variant_id))

            variant = ImageVariant.objects.filter(id=variant_id).first()
            if not variant:
                logger.error("Variant not found")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            if variant.file_type == "avif":
                content_type = "image/avif"
            elif variant.file_type == "webp":
                content_type = "image/webp"
            else:
                content_type = "binary/octet-stream"

            bucket = get_b2_resource()

            bucket.upload_fileobj(
                variant_file,
                variant.backblaze_filepath,
                ExtraArgs={"ContentType": content_type},
            )

            variant.available = True
            variant.save()

            logger.info("Processed variant {}".format(variant_id))

            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue="task_queue", on_message_callback=callback)

        channel.start_consuming()
