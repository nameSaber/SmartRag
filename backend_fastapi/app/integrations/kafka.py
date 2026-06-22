import asyncio
import json

from aiokafka import AIOKafkaProducer

from app.core.config import settings


class KafkaTaskPublisher:
    def __init__(self, bootstrap_servers: str | None = None, topic: str | None = None):
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.topic = topic or settings.file_processing_topic

    async def publish_async(self, payload: dict) -> None:
        producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        await producer.start()
        try:
            await producer.send_and_wait(self.topic, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        finally:
            await producer.stop()

    def publish(self, payload: dict) -> None:
        # FastAPI 同步接口中发布 Kafka 任务，避免把 Kafka 细节泄漏到业务服务层。
        asyncio.run(self.publish_async(payload))


def get_task_publisher() -> KafkaTaskPublisher:
    return KafkaTaskPublisher()

