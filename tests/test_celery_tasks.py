from flash.celery_app import dead_letter_queue, dlx, main_queue
from flash.celery_tasks import send_password_reset_email_celery


def test_main_queue_dead_letters_to_the_dlx() -> None:
    assert main_queue.queue_arguments == {"x-dead-letter-exchange": dlx.name}


def test_dead_letter_queue_is_bound_with_a_matching_routing_key() -> None:
    """Guards against the exact mistake made while building this: if the DLQ's
    routing key ever drifts from the main queue's, rejected messages are
    dead-lettered to the right exchange but match no binding and silently
    vanish instead of landing in the DLQ."""
    assert dead_letter_queue.exchange.name == dlx.name
    assert dead_letter_queue.routing_key == main_queue.routing_key


def test_retries_only_on_connection_errors() -> None:
    """Guards against silently widening this to retry on everything (e.g.
    `Exception`), which would keep retrying permanent failures forever."""
    assert send_password_reset_email_celery.autoretry_for == (ConnectionError,)


def test_uses_backoff_with_jitter_and_a_retry_limit() -> None:
    assert send_password_reset_email_celery.retry_backoff is True
    assert send_password_reset_email_celery.retry_backoff_max == 60
    assert send_password_reset_email_celery.retry_jitter is True
    assert send_password_reset_email_celery.max_retries == 5
