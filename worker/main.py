import base64
import functools
import json
import subprocess
import os
import pika
import re


def processing_function(func):
    @functools.wraps(func)
    def callback(self, ch, method, properties, body):
        args = json.loads(body.decode("utf-8"))

        original_file = base64.b64decode(args["original_file"])
        variant_id = args["variant_id"]

        print(f"Processing variant {variant_id}")

        input_file = f"{variant_id}_original"
        output_file = f"{variant_id}_processed"

        with open(input_file, "wb") as original_image:
            original_image.write(original_file)

        print("Converting image...")
        try:
            func(self, input_file, output_file)
        except Exception as e:
            print(e)
            os.remove(input_file)
            try:
                os.remove(output_file)
            except:
                pass
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        print("Image converted!")

        with open(output_file, "rb") as f:
            image = f.read()

        message = {
            "variant_id": variant_id,
            "variant_file": base64.b64encode(image).decode("utf-8"),
        }

        print("Sending converted file...")

        self.channel.basic_publish(
            exchange="",
            routing_key="process_variant",
            body=json.dumps(message).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
        )

        print("File sent!")

        os.remove(input_file)
        os.remove(output_file)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    return callback


class Worker:
    def __init__(self):
        connection_parameters = self.make_rabbitmq_parameters()
        self.connection = pika.BlockingConnection(connection_parameters)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue="kakigoori_avif", durable=True)
        self.channel.queue_declare(queue="kakigoori_webp", durable=True)
        self.channel.queue_declare(queue="process_variant", durable=True)
        self.channel.basic_qos(prefetch_count=1)

        worker_file_types = re.split(
            r"[,;-_ /]", os.environ.get("WORKER_FILE_TYPES", "").lower()
        )

        if not any(worker_file_types):
            worker_file_types = ["avif", "webp"]

        print(worker_file_types)

        if "avif" in worker_file_types:
            self.channel.basic_consume(
                queue="kakigoori_avif", on_message_callback=self.avif_processing
            )
        if "webp" in worker_file_types:
            self.channel.basic_consume(
                queue="kakigoori_webp", on_message_callback=self.webp_processing
            )

        print("Ready to accept requests")

    def make_rabbitmq_parameters(self):
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

        return connection_parameters

    @processing_function
    def avif_processing(self, input_file, output_file):
        subprocess.run(
            [
                *"/usr/bin/avifenc -y 420".split(" "),
                input_file,
                output_file,
            ],
            check=True,
        )

    @processing_function
    def webp_processing(self, input_file, output_file):
        subprocess.run(
            [
                "cwebp",
                "-metadata",
                "icc",
                input_file,
                "-o",
                output_file,
            ]
        )


worker = Worker()

try:
    worker.channel.start_consuming()
except Exception as e:
    worker.channel.stop_consuming()

print("Exiting...")
worker.connection.close()
