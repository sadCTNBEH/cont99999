import datetime
import os
from threading import Thread

import aiofiles.os
import aiofiles
import asyncio
import pytesseract
from PIL import Image
from sqlalchemy import select, update
from fastapi import FastAPI, HTTPException, UploadFile
from dotenv import load_dotenv
from DataBaseModelsAndLogic import Documents, Documents_text, SessionDep, get_session
from alembic_run import run_migration

load_dotenv()
language = os.getenv("LANGUAGE")

app = FastAPI(
    title="Slow API",
    description="Какое-то описание, что-то делает",
    version="0.0.0.0.0.0.1"
)


@app.on_event("startup")
async def startup_event():
    thread = Thread(target=run_migration)
    thread.start()
    thread.join()


@app.post("/upload_doc", summary="Загрузить документ",
          description="Принимает катинку .jpg и возвращает путь к ней на диске, записывает в бд")
async def upload_doc(file: UploadFile):
    await aiofiles.os.makedirs("documents", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filepath = os.path.join("documents", f"doc{timestamp}.jpg")

    file_bytes = await file.read()

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(file_bytes)

    new_doc = Documents(
        path=filepath,
        date=timestamp
    )
    new_doc.doc = Documents_text(text="NOT ANALYSED")
    async with get_session() as session:
        session.add(new_doc)
        await session.commit()
    return {"UploadFile": "Success", "filepath": filepath, "id": new_doc.id}


async def get_path(doc_id: int) -> str:
    async with get_session() as session:
        query = select(Documents.path).where(Documents.id == doc_id)
        result = await session.execute(query)
        filepath = result.scalar()
    return filepath


async def process_image_async(doc_id: int):
    async with get_session() as session:
        filepath = await get_path(doc_id)
        loop = asyncio.get_event_loop()
        img = await loop.run_in_executor(None, Image.open, str(filepath))
        text_on_img = await loop.run_in_executor(None, pytesseract.image_to_string, img, language)
        result = text_on_img.replace("\n", "")

        await session.execute(
            update(Documents_text).where(Documents_text.id_doc == doc_id).values(text=result)
        )
        await session.commit()


@app.patch("/doc_analyse/{doc_id}", summary="Анализ текста",
           description="Анализирует текст с картинки, записывает в бд, англ язык.")
async def celery_task_endpoint(doc_id: int):
    from celery_app import process_image_task
    process_image_task.delay(doc_id)
    return {"Analyse Task": "Sended"}


@app.get("/get_text/{doc_id}", summary="Получить текст",
         description="Получает текст из БД")
async def get_text(doc_id: int):
    async with get_session() as session:
        query = select(Documents_text.text).where(Documents_text.id_doc == doc_id)
        result = await session.execute(query)
    return {"Text on image": result.scalar()}


@app.delete("/doc_delete/{doc_id}", summary="Удалить документ",
            description="Удаляет документ из БД и из файловой системы")
async def doc_delete(doc_id: int):
    filepath = await get_path(doc_id)
    async with get_session() as session:
        doc = await session.get(Documents, doc_id)
        if doc:
            await session.delete(doc)
            await session.commit()

        if not filepath:
            raise HTTPException(status_code=404, detail="ID не найден")

        if await aiofiles.os.path.exists(filepath):
            await aiofiles.os.remove(filepath)

    return {"File": "Deleted", "filepath": filepath}
