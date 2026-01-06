"""
Сервис для управления мульти-тенантностью.

Этот модуль обеспечивает:
- Создание tenant схем для каждой компании
- Клонирование таблиц в tenant схемы
- Управление tenant сессиями
- Переключение между схемами
"""

import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import Session

from app.config import settings
from app.models.public_models import Company

logger = logging.getLogger(__name__)


class TenantService:
    """Сервис для управления tenant-схемами."""
    
    def __init__(self):
        """Инициализация сервиса."""
        self._engine: Optional[AsyncEngine] = None
        self._async_session_maker: Optional[async_sessionmaker] = None
    
    async def _get_engine(self) -> AsyncEngine:
        """
        Получить или создать engine для tenant схем.
        
        Returns:
            AsyncEngine для работы с tenant схемами
        """
        if self._engine is None:
            # Формируем URL базы данных
            # Используем postgresql:// для поддержки search_path
            db_url = (
                f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
                f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            )
            
            # Создаем engine без echo для production
            self._engine = create_async_engine(
                db_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )
            
            self._async_session_maker = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            logger.info("Tenant engine создан")
        
        return self._engine
    
    async def _get_async_session_maker(self) -> async_sessionmaker:
        """
        Получить async session maker.
        
        Returns:
            AsyncSessionMaker для tenant схем
        """
        await self._get_engine()
        return self._async_session_maker
    
    async def tenancy_schema_exists(self, company_id: int) -> bool:
        """
        Проверить, существует ли tenant схема для компании.
        
        Args:
            company_id: ID компании
        
        Returns:
            True, если схема существует, иначе False
        """
        logger.info(f"Проверка существования tenant схемы для компании {company_id}")
        
        engine = await self._get_engine()
        
        try:
            # Создаем временную сессию для проверки
            async with self._async_session_maker() as session:
                # Выполняем SQL запрос для проверки существования схемы
                schema_name = f"tenant_{company_id}"
                result = await session.execute(
                    text(f"""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.schemata 
                            WHERE schema_name = '{schema_name}'
                        )
                    """)
                )
                exists = result.scalar()
                
                if exists:
                    logger.info(f"Tenant схема '{schema_name}' существует")
                else:
                    logger.info(f"Tenant схема '{schema_name}' не существует")
                
                return exists
        except Exception as e:
            logger.error(f"Ошибка при проверке tenant схемы '{schema_name}': {e}")
            return False
    
    async def create_tenant_schema(self, company_id: int) -> bool:
        """
        Создать tenant схему для компании.
        
        Args:
            company_id: ID компании
        
        Returns:
            True, если схема успешно создана, иначе False
        """
        schema_name = f"tenant_{company_id}"
        logger.info(f"Создание tenant схемы '{schema_name}' для компании {company_id}")
        
        engine = await self._get_engine()
        
        try:
            # Создаем схему
            async with self._async_session_maker() as session:
                await session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
                await session.commit()
            
            logger.info(f"Tenant схема '{schema_name}' успешно создана")
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании tenant схемы '{schema_name}': {e}")
            return False
    
    async def clone_table_to_tenant(self, company_id: int, table_name: str) -> bool:
        """
        Клонировать таблицу из public схемы в tenant схему.
        
        Args:
            company_id: ID компании
            table_name: Имя таблицы для клонирования
        
        Returns:
            True, если таблица успешно склонирована, иначе False
        """
        schema_name = f"tenant_{company_id}"
        logger.info(f"Клонирование таблицы '{table_name}' в '{schema_name}'")
        
        engine = await self._get_engine()
        
        try:
            async with self._async_session_maker() as session:
                # Клонируем таблицу (структуру + данные)
                # Если таблица существует в tenant, сначала удаляем
                await session.execute(
                    text(f'DROP TABLE IF EXISTS "{schema_name}"."{table_name} CASCADE')
                )
                
                # Клонируем таблицу из public в tenant схему
                await session.execute(
                    text(f'CREATE TABLE "{schema_name}"."{table_name}" '
                          f'AS SELECT * FROM public."{table_name}')
                )
                
                # Восстанавливаем последовательности
                await session.execute(
                    text(f"SELECT setval(pg_get_serial_sequence('{schema_name}.{table_name}_id_seq'::regclass), max(id)) "
                          f"FROM \"{schema_name}\".{table_name}")
                )
                
                await session.commit()
            
            logger.info(f"Таблица '{table_name}' успешно склонирована в '{schema_name}'")
            return True
        except Exception as e:
            logger.error(f"Ошибка при клонировании таблицы '{table_name}' в '{schema_name}': {e}")
            return False
    
    async def initialize_tenant_for_company(self, company_id: int) -> bool:
        """
        Инициализировать tenant схему для новой компании.
        
        Args:
            company_id: ID компании
        
        Returns:
            True, если инициализация успешна, иначе False
        """
        logger.info(f"Инициализация tenant схемы для компании {company_id}")
        
        # Список таблиц для клонирования
        # В будущем можно добавить больше таблиц
        tables_to_clone = [
            "users",
            "services",
            "masters",
            "bookings",
            "clients",
            "posts",
            "slots",
            "notifications",
            "settings",
            "blocks",
            "promocodes",
            "promotions",
        ]
        
        try:
            # 1. Создаем tenant схему
            if not await self.tenancy_schema_exists(company_id):
                if not await self.create_tenant_schema(company_id):
                    logger.error(f"Не удалось создать tenant схему для компании {company_id}")
                    return False
            
            # 2. Клонируем все таблицы
            success_count = 0
            for table_name in tables_to_clone:
                if await self.clone_table_to_tenant(company_id, table_name):
                    success_count += 1
                else:
                    logger.error(f"Не удалось склонировать таблицу '{table_name}'")
            
            logger.info(f"Инициализация tenant схемы завершена: {success_count}/{len(tables_to_clone)} таблиц склонировано")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации tenant схемы для компании {company_id}: {e}")
            return False
    
    async def drop_tenant_schema(self, company_id: int) -> bool:
        """
        Удалить tenant схему компании.
        
        Args:
            company_id: ID компании
        
        Returns:
            True, если схема успешно удалена, иначе False
        """
        schema_name = f"tenant_{company_id}"
        logger.warning(f"Удаление tenant схемы '{schema_name}' для компании {company_id}")
        
        engine = await self._get_engine()
        
        try:
            async with self._async_session_maker() as session:
                # Удаляем схему и все данные
                await session.execute(
                    text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
                )
                await session.commit()
            
            logger.info(f"Tenant схема '{schema_name}' удалена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении tenant схемы '{schema_name}': {e}")
            return False
    
    @asynccontextmanager
    async def get_tenant_session(self, company_id: int):
        """
        Получить асинхронную сессию для работы с tenant схемой компании.
        
        Args:
            company_id: ID компании
            
        Yields:
            AsyncSession для tenant схемы
        """
        schema_name = f"tenant_{company_id}"
        logger.info(f"Получение tenant сессии для компании {company_id} (схема: {schema_name})")
        
        async_session_maker = await self._get_async_session_maker()
        async with async_session_maker() as session:
            # Устанавливаем search_path для tenant схемы
            await session.execute(
                text(f"SET search_path TO \"{schema_name}\"")
            )
            await session.commit()
        
        async with async_session_maker() as session:
            # Устанавливаем search_path для каждой транзакции
            await session.execute(
                text(f"SET search_path TO \"{schema_name}\"")
            )
            
            yield session


# Глобальный экземпляр сервиса
_tenant_service: Optional[TenantService] = None


def get_tenant_service() -> TenantService:
    """
    Получить глобальный экземпляр TenantService.
    
    Returns:
        Экемпляр TenantService
    """
    global _tenant_service
    if _tenant_service is None:
        _tenant_service = TenantService()
        logger.info("TenantService создан")
    return _tenant_service
