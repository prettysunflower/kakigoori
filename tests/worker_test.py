import base64
import io
import json
import logging
import os
import sys
import uuid

import PIL.Image
import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.rabbitmq import RabbitMqContainer
from testcontainers.core.image import DockerImage
import pika

rabbitmq_host = str(uuid.uuid4())

network = Network()
rabbitmq = RabbitMqContainer(
    "rabbitmq:4.1.4",
    network=network,
    network_aliases=rabbitmq_host,
    name=rabbitmq_host,
)
docker_image = DockerImage(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "worker")
)

logger = logging.getLogger()


@pytest.fixture(scope="module", autouse=True)
def setup(request):
    network.create()
    docker_image.build()
    rabbitmq.start()
    kakigoori_worker = DockerContainer(
        str(docker_image),
        env={
            "RABBITMQ_ADDRESS": f"amqp://{rabbitmq_host}:{rabbitmq.port}/{rabbitmq.vhost}",
        },
        network=network,
    )
    kakigoori_worker.start()

    def cleanup():
        kakigoori_worker.stop()
        rabbitmq.stop()
        docker_image.remove()
        network.remove()

    request.addfinalizer(cleanup)


@pytest.mark.parametrize("file_format", ["avif", "webp"])
def test_worker(file_format):
    connection = pika.BlockingConnection(rabbitmq.get_connection_params())
    channel = connection.channel()
    queue = f"kakigoori_{file_format}"
    channel.queue_declare(queue=queue, durable=True)
    channel.queue_declare(queue="process_variant", durable=True)

    def process_variant_callback(ch, method, properties, body):
        logger.info(f" [x] Received body!")
        args = json.loads(body.decode("utf-8"))
        variant_file = base64.b64decode(args["variant_file"])
        image = PIL.Image.open(io.BytesIO(variant_file))
        logger.info(image.format)
        assert image.format.lower() == file_format
        channel.stop_consuming()
        connection.close()

    channel.basic_consume(
        queue="process_variant",
        on_message_callback=process_variant_callback,
        auto_ack=True,
    )

    with open(os.path.join(os.path.dirname(__file__), "103328382_p0.jpg"), "rb") as f:
        image = f.read()

    message = {
        "variant_id": "test",
        "original_file": base64.b64encode(image).decode("utf-8"),
    }

    logger.info("Sending message")

    channel.basic_publish(
        exchange="",
        routing_key=queue,
        body=json.dumps(message).encode("utf-8"),
        properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
    )

    channel.start_consuming()
