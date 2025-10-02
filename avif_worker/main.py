# /// script
# dependencies = [
#   "pika",
# ]
# ///

import base64
import json
import subprocess
import os
import pika

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST")
if not RABBITMQ_HOST:
    raise ValueError("RABBITMQ_HOST environment variable is not set")

RABBITMQ_PORT = os.environ.get("RABBITMQ_PORT")
if not RABBITMQ_PORT:
    RABBITMQ_PORT = 5672

connection_parameters = pika.ConnectionParameters(
    host=RABBITMQ_HOST, port=RABBITMQ_PORT
)

if os.environ.get("RABBITMQ_USER") and os.environ.get("RABBITMQ_PASSWORD"):
    RABBITMQ_USER = os.environ.get("RABBITMQ_USER")
    RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD")
    connection_parameters.credentials = pika.PlainCredentials(
        username=RABBITMQ_USER, password=RABBITMQ_PASSWORD
    )

if os.environ.get("RABBITMQ_VHOST"):
    connection_parameters.virtual_host = os.environ.get("RABBITMQ_VHOST")

connection = pika.BlockingConnection(connection_parameters)
channel = connection.channel()

print("Started worker")

channel.queue_declare(queue="kakigoori_avif", durable=True)
channel.queue_declare(queue="process_variant", durable=True)


def callback(ch, method, properties, body):
    args = json.loads(body.decode("utf-8"))

    original_file = base64.b64decode(args["original_file"])
    variant_id = args["variant_id"]

    print(f"Processing variant {variant_id}")

    with open(f"avif_{variant_id}", "wb") as original_image:
        original_image.write(original_file)

    try:
        subprocess.run(
            [
                *"/usr/bin/avifenc -y 420".split(" "),
                f"avif_{variant_id}",
                f"avif_{variant_id}.avif",
            ],
            check=True,
        )

    except subprocess.CalledProcessError as e:
        print(e.output)
        print(f"AVIF Ignore {variant_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    with open(f"avif_{variant_id}.avif", "rb") as f:
        image = f.read()

    message = {
        "variant_id": variant_id,
        "variant_file": base64.b64encode(image).decode("utf-8"),
    }

    channel.basic_publish(
        exchange="",
        routing_key="process_variant",
        body=json.dumps(message).encode("utf-8"),
        properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
    )

    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue="kakigoori_avif", on_message_callback=callback)

print("Ready to accept requests")

channel.start_consuming()
