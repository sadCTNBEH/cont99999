import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy import MetaData, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import as_declarative, Mapped, mapped_column, relationship
from dotenv import load_dotenv


load_dotenv()
database_url = os.getenv("DATABASE_URL")

engine = create_async_engine(database_url, echo=True)

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
