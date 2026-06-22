import asyncio
import json

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.core.database import SessionLocal
from app.tasks.file_processing import process_file_task


async def consume_file_processing() -> None:
    consumer = AIOKafkaConsumer(
        settings.file_processing_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="smart-rag-file-processing",
        enable_auto_commit=False,
    )
    await consumer.start()
    try:
        async for message in consumer:
            payload = json.loads(message.value.decode("utf-8"))
            db = SessionLocal()
            try:
                process_file_task(db, payload)
                await consumer.commit()
            finally:
                db.close()
    finally:
        await consumer.stop()


def main() -> None:
    # 独立消费者入口：python -m app.consumers.file_processing_consumer
    asyncio.run(consume_file_processing())


if __name__ == "__main__":
    main()

