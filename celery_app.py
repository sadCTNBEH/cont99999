from celery import Celery
from main import process_image_async
import asyncio

app = Celery('tasks', broker='redis://redis:6379/0')

app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
)

@app.task(name='tasks.process_image_async')
def process_image_task(doc_id: int):
    asyncio.run(process_image_async(doc_id))