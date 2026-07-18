from celery import Celery
from kombu import Exchange, Queue
from flash.core.config import get_settings

celery_app = Celery(
    "flash", broker=get_settings().rabbitmq_url, include=["flash.workers.tasks"]
)
# Requires tasks to be safe to run more than once
celery_app.conf.task_acks_late = True
# when max retry reached does not aknowledge the message
celery_app.conf.task_acks_on_failure_or_timeout = False

dlx = Exchange("flash.dlx", type="direct")
main_queue = Queue(
    "celery",
    exchange=Exchange("celery", type="direct"),
    routing_key="celery",
    queue_arguments={"x-dead-letter-exchange": "flash.dlx"},
)
dead_letter_queue = Queue("flash.dlq", exchange=dlx, routing_key="celery")
celery_app.conf.task_queues = (main_queue,)
celery_app.conf.task_default_queue = "celery"


@celery_app.on_after_configure.connect  # type: ignore[untyped-decorator]
def declare_dead_letter_queue(sender: Celery, **kwargs: object) -> None:
    """The worker only declares queues it actually consumes from (see
    docker-compose.yaml's `-Q celery`), so the DLQ needs its own explicit
    declaration here -- it's never consumed from, only ever routed into."""
    with sender.connection_for_write() as conn:
        dead_letter_queue.bind(conn).declare()
