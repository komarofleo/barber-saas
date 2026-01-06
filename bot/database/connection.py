"""Подключение к базе данных"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from bot.config import DATABASE_URL
from shared.database.models import Base

# Создаем движок
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

# Создаем фабрику сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session() -> AsyncSession:
    """Получить сессию БД"""
    async with async_session_maker() as session:
        yield session

async def get_async_session():
    """
    Получить асинхронную сессию БД (без контекст менеджера).
    
    Returns:
        Асинхронная сессия
    """
    async with async_session_maker() as session:
        yield session

async def init_db():
    """Инициализация БД (создание таблиц)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """Закрыть соединение с БД"""
    await engine.dispose()

async def get_async_session():
    """
    Получить асинхронную сессию БД (без контекст менеджера).
    
    Returns:
        Асинхронная сессия
    """
    async with async_session_maker() as session:
        yield session

async def init_db():
    """Инициализация БД (создание таблиц)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """Закрыть соединение с БД"""
    await engine.dispose()
