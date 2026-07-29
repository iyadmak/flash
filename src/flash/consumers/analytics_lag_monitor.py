"""Lag monitor for the flash-analytics consumer group.

Never joins the group -- it reads committed offsets through the admin API -- so it
still reports lag when the analytics consumer has died, without stealing work.
"""

import asyncio
import structlog
from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient
from aiokafka.structs import TopicPartition
from flash.consumers.analytics import CONSUMER_GROUP, TOPIC
from flash.core.config import get_settings

logger = structlog.get_logger()

CHECK_INTERVAL_SECONDS = 15


async def check_lag(admin: AIOKafkaAdminClient, consumer: AIOKafkaConsumer) -> None:
    partitions = consumer.partitions_for_topic(TOPIC)
    if not partitions:
        logger.warning("lag_check_no_partitions", topic=TOPIC)
        return

    topic_partitions = [
        TopicPartition(TOPIC, partition) for partition in sorted(partitions)
    ]
    end_offsets = await consumer.end_offsets(topic_partitions)
    committed = await admin.list_consumer_group_offsets(
        CONSUMER_GROUP, partitions=topic_partitions
    )

    total_lag = 0
    for topic_partition in topic_partitions:
        end_offset = end_offsets[topic_partition]
        committed_metadata = committed.get(topic_partition)
        # A group that has never committed reports -1; treat that as offset zero.
        committed_offset = (
            committed_metadata.offset
            if committed_metadata and committed_metadata.offset >= 0
            else 0
        )
        lag = end_offset - committed_offset
        total_lag += lag
        logger.info(
            "partition_lag",
            group=CONSUMER_GROUP,
            topic=TOPIC,
            partition=topic_partition.partition,
            end_offset=end_offset,
            committed_offset=committed_offset,
            lag=lag,
        )
    logger.info("total_lag", group=CONSUMER_GROUP, topic=TOPIC, total_lag=total_lag)


async def main() -> None:
    settings = get_settings()
    admin = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers)
    # Passing TOPIC is what populates partitions_for_topic()'s cache; fetch_all_
    # metadata() updates a copy it never reads. No group_id: it must not join.
    consumer = AIOKafkaConsumer(
        TOPIC, bootstrap_servers=settings.kafka_bootstrap_servers
    )
    await admin.start()
    await consumer.start()
    try:
        while True:
            await check_lag(admin, consumer)
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
    finally:
        await consumer.stop()
        await admin.close()


if __name__ == "__main__":
    asyncio.run(main())
