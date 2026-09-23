import os

from faststream.middlewares import AckPolicy
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue


RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost:5672/",
)

DEAD_LETTER_EXCHANGE = RabbitExchange("payments.dlx", durable=True)
DEAD_LETTER_QUEUE = RabbitQueue(
    "payments.dlq",
    durable=True,
    routing_key="payments.dlq",
)
PAYMENTS_QUEUE = RabbitQueue(
    "payments.new",
    durable=True,
    arguments={
        "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE.name,
        "x-dead-letter-routing-key": DEAD_LETTER_QUEUE.routing(),
    },
)

broker = RabbitBroker(RABBITMQ_URL, ack_policy=AckPolicy.REJECT_ON_ERROR)

# Registering the publisher makes FastStream declare the DLX and its queue on startup.
dead_letter_publisher = broker.publisher(
    queue=DEAD_LETTER_QUEUE,
    exchange=DEAD_LETTER_EXCHANGE,
)
payment_publisher = broker.publisher(queue=PAYMENTS_QUEUE)
