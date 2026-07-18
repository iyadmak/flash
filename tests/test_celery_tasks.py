from flash.celery_tasks import send_password_reset_email_celery


def test_retries_only_on_connection_errors() -> None:
    """Guards against silently widening this to retry on everything (e.g.
    `Exception`), which would keep retrying permanent failures forever."""
    assert send_password_reset_email_celery.autoretry_for == (ConnectionError,)


def test_uses_backoff_with_jitter_and_a_retry_limit() -> None:
    assert send_password_reset_email_celery.retry_backoff is True
    assert send_password_reset_email_celery.retry_backoff_max == 60
    assert send_password_reset_email_celery.retry_jitter is True
    assert send_password_reset_email_celery.max_retries == 5
