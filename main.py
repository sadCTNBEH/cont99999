import base64
import datetime
import os
from contextlib import asynccontextmanager
from typing import Annotated

import aiofiles.os
import aiofiles
import asyncio
import pytesseract
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import ForeignKey, MetaData, select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import as_declarative, Mapped, mapped_column, relationship
from fastapi import FastAPI, Depends, HTTPException

app = FastAPI(
    title="Slow API",
    description="Какое-то описание, что-то делает",
    version="0.0.0.0.0.0.1"
)

engine = create_async_engine("sqlite+aiosqlite:///docs.db", echo=True)

new_session = async_sessionmaker(engine, expire_on_commit=False)

@asynccontextmanager
async def get_session():
    async with new_session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


@as_declarative()
class Base:
    metadata = MetaData()
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class Documents(Base):
    __tablename__ = "documents"

    path: Mapped[str] = mapped_column()
    date: Mapped[str] = mapped_column()
    doc: Mapped["Documents_text"] = relationship(back_populates="doc_text", uselist=False, cascade="all, delete-orphan",
                                                 single_parent=True)

    def __repr__(self):
        return f"{self.id=}, {self.path=}, {self.date=}"


class Documents_text(Base):
    __tablename__ = "documents_text"

    id_doc: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    text: Mapped[str] = mapped_column()
    doc_text: Mapped["Documents"] = relationship(back_populates="doc", uselist=False, foreign_keys=[id_doc])

    def __repr__(self):
        return f"{self.id_doc=}, {self.text=}, {self.doc_text=}"


@app.post("/setup_db", summary="Создать базу данных",
         description="Удаляет старую БД, если она была и создает новую")
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return {"Success": "True"}


class UploadDocSchema(BaseModel):
    imageb64: str

@app.post("/upload_doc", summary="Загрузить документ",
         description="Принимает строку base64, создает .jpg и возвращает путь к нему")
async def upload_doc(data: UploadDocSchema, session: SessionDep):
    imagedata = base64.b64decode(data.imageb64)
    await aiofiles.os.makedirs("documents", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filepath = os.path.join("documents", f"doc{timestamp}.jpg")

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(imagedata)

    new_doc = Documents(
        path=filepath,
        date=timestamp
    )
    new_doc.doc = Documents_text(text="NOT ANALYSED")
    async with get_session() as session:
        session.add(new_doc)
        await session.commit()
    return {"Success": "True", "filepath": filepath}


async def get_path(doc_id: int, session: SessionDep) -> str:
    async with get_session() as session:
        query = select(Documents.path).where(Documents.id == doc_id)
        result = await session.execute(query)
        filepath = result.scalar()
    return filepath

async def process_image_async(doc_id: int):
    async with get_session() as session:
        filepath = await get_path(doc_id, session)
        loop = asyncio.get_event_loop()
        img = await loop.run_in_executor(None, Image.open, str(filepath))
        text_on_img = await loop.run_in_executor(None, pytesseract.image_to_string, img, "eng")
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
    return {"success": "True"}


@app.get("/get_text/{doc_id}", summary="Получить текст",
         description="Получает текст из БД")
async def get_text(doc_id: int, session: SessionDep):
    async with get_session() as session:
        query = select(Documents_text.text).where(Documents_text.id_doc == doc_id)
        result = await session.execute(query)
    return {"text": result.scalar()}
    

@app.delete("/doc_delete/{doc_id}", summary="Удалить документ",
         description="Удаляет документ из БД и из файловой системы")
async def doc_delete(doc_id: int, session: SessionDep):
    filepath = await get_path(doc_id, session)
    async with get_session() as session:
        doc = await session.get(Documents, doc_id)
        if doc:
            await session.delete(doc)
            await session.commit()

        if not filepath:
            raise HTTPException(status_code=404, detail="ID не найден")

        if await aiofiles.os.path.exists(filepath):
            await aiofiles.os.remove(filepath)

    return {"Success": "True", "filepath": filepath}