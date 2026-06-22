import asyncio
import json

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.core.database import SessionLocal
from app.tasks.file_processing import process_file_task


async def consume_file_processing() -> None:
    """持续消费文件处理主题。

    消息处理成功后才手动提交 offset，避免消费者异常退出时丢失未完成的向量化任务。
    """
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
                # 每条消息使用独立数据库会话，确保失败任务不会污染后续消息处理。
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
