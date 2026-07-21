"""Continuously-running, standalone lag monitor for the flash-analytics
consumer group. Deliberately never joins that group -- it only reads
committed offsets via the admin API (list_consumer_group_offsets) and the
latest offset per partition via a groupless consumer, so it can observe lag
even if analytics_consumer has silently died, without ever stealing its
partitions."""

import asyncio
import structlog
from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient
from aiokafka.structs import TopicPartition
from flash.consumers.analytics import CONSUMER_GROUP, TOPIC
from flash.core.config import get_settings

logger = structlog.get_logger()

CHECK_INTERVAL_SETTINGS = 15


async def check_lag(admin: AIOKafkaAdminClient, consumer: AIOKafkaConsumer) -> None:
    partitions = consumer.partitions_for_topic(TOPIC)
    if not partitions:
        logger.warning("lag_check_no_partitions", topic=TOPIC)
        return

    topic_partitions = [TopicPartition(TOPIC, p) for p in sorted(partitions)]
    end_offsets = await consumer.end_offsets(topic_partitions)
    committed = await admin.list_consumer_group_offsets(
        CONSUMER_GROUP, partitions=topic_partitions
    )

    total_lag = 0
    for tp in topic_partitions:
        end_offset = end_offsets[tp]
        commited_offset = committed.get(tp)
        current = (
            commited_offset.offset
            if commited_offset and commited_offset.offset >= 0
            else 0
        )
        lag = end_offset - current
        total_lag += lag
        logger.info(
            "partition_lag",
            group=CONSUMER_GROUP,
            topic=TOPIC,
            partition=tp.partition,
            end_offset=end_offset,
            commited_offset=current,
            lag=lag,
        )
    logger.info("total_lag", group=CONSUMER_GROUP, topic=TOPIC, total_lag=total_lag)


async def main() -> None:
    settings = get_settings()
    admin = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers)
    # Passing TOPIC here (rather than a bare, topic-less consumer) is what
    # actually populates partitions_for_topic()'s local cache -- verified
    # empirically; fetch_all_metadata()/topics() update a disconnected
    # metadata copy that partitions_for_topic() never reads from. Still no
    # group_id: this consumer never joins flash-analytics.
    consumer = AIOKafkaConsumer(
        TOPIC, bootstrap_servers=settings.kafka_bootstrap_servers
    )
    await admin.start()
    await consumer.start()
    try:
        while True:
            await check_lag(admin, consumer)
            await asyncio.sleep(CHECK_INTERVAL_SETTINGS)
    finally:
        await consumer.stop()
        await admin.close()


if __name__ == "__main__":
    asyncio.run(main())
