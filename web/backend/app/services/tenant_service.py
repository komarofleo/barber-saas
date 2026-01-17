"""
Сервис для управления мульти-тенантностью (ИСПРАВЛЕННАЯ ВЕРСИЯ).

Этот модуль обеспечивает:
- Создание tenant схем для каждой компании
- Клонирование таблиц в tenant схемы
- Управление tenant сессиями
- Переключение между схемами

**ИСПРАВЛЕНИЯ:**
- Исправлена ошибка с self._async_session_maker = None
- Все методы (create, drop, clone) используют await self._get_async_session_maker()
"""
import logging
from typing import Optional, AsyncGenerator
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
        self._initialized_companies: set[int] = set()
    
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
            # Увеличиваем размер пула для предотвращения переполнения
            self._engine = create_async_engine(
                db_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )
        
        return self._engine
    
    async def _get_async_session_maker(self) -> async_sessionmaker:
        """
        Получить или создать session maker для tenant схем.
        
        Returns:
            AsyncSessionMaker для создания сессий
        """
        if self._async_session_maker is None:
            engine = await self._get_engine()
            self._async_session_maker = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        
        return self._async_session_maker
    
    async def tenancy_schema_exists(self, company_id: int) -> bool:
        """
        Проверить существование tenant схемы.
        
        Args:
            company_id: ID компании
            
        Returns:
            True, если схема существует, иначе False
        """
        schema_name = f"tenant_{company_id}"
        engine = await self._get_engine()
        
        try:
            async_session_maker = await self._get_async_session_maker()
            async with async_session_maker() as session:
                result = await session.execute(
                    text(f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema_name"),
                    {"schema_name": schema_name}
                )
                return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Ошибка при проверке существования схемы '{schema_name}': {e}")
            return False
    
    async def create_tenant_schema(self, company_id: int) -> bool:
        """
        Создать tenant схему для новой компании.
        
        Args:
            company_id: ID компании
            
        Returns:
            True, если схема успешно создана, иначе False
        """
        schema_name = f"tenant_{company_id}"
        logger.info(f"Создание tenant схемы '{schema_name}' для компании {company_id}")
        
        engine = await self._get_engine()
        
        try:
            async_session_maker = await self._get_async_session_maker()
            async with async_session_maker() as session:
                await session.execute(text(f'CREATE SCHEMA "{schema_name}"'))
                await session.commit()
            
            logger.info(f"Tenant схема '{schema_name}' создана")
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
            async_session_maker = await self._get_async_session_maker()
            async with async_session_maker() as session:
                # Создаем таблицу в tenant схеме без копирования данных
                await session.execute(
                    text(
                        f'CREATE TABLE IF NOT EXISTS "{schema_name}"."{table_name}" '
                        f'AS SELECT * FROM public."{table_name}" WHERE false'
                    )
                )
                
                if table_name == "users":
                    # Добавляем колонки, которые использует бот (совместимость с tenant-схемой)
                    await session.execute(
                        text(
                            f'ALTER TABLE "{schema_name}"."{table_name}" '
                            'ADD COLUMN IF NOT EXISTS full_name VARCHAR(255), '
                            'ADD COLUMN IF NOT EXISTS role VARCHAR(50), '
                            'ADD COLUMN IF NOT EXISTS is_active BOOLEAN, '
                            'ADD COLUMN IF NOT EXISTS password_hash TEXT'
                        )
                    )
                
                # Восстанавливаем последовательности (если есть)
                # Проверяем существование последовательности перед setval
                await session.execute(
                    text(f"""
                        DO $$
                            DECLARE seq_name TEXT;
                            BEGIN
                                SELECT 'tenant_{company_id}.' || :table_name || '_id_seq' INTO seq_name;
                                IF EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = seq_name) THEN
                                    PERFORM setval(seq_name::regclass, COALESCE((SELECT MAX(id) FROM "{schema_name}"."{table_name}"), 1));
                                END IF;
                            END $$;
                        """),
                    {"table_name": table_name, "company_id": company_id}
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
        
        tables_to_clone = [
            "users",
            "services",
            "masters",
            "bookings",
            "clients",
            "posts",
            "timeslots",
            "notifications",
            "settings",
            "broadcasts",
            "blocked_slots",
            "promocodes",
            "promotions",
        ]
        
        try:
            if not await self.tenancy_schema_exists(company_id):
                if not await self.create_tenant_schema(company_id):
                    logger.error(f"Не удалось создать tenant схему для компании {company_id}")
                    return False
            
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
            async_session_maker = await self._get_async_session_maker()
            async with async_session_maker() as session:
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
    
    async def get_tenant_session(self, company_id: int) -> AsyncGenerator[AsyncSession, None]:
        """
        Получить асинхронную сессию для работы с tenant схемой компании.
        
        Args:
            company_id: ID компании
            
        Yields:
            AsyncSession для tenant схемы
        """
        schema_name = f"tenant_{company_id}"
        logger.info(f"Получение tenant сессии для компании {company_id} (схема: {schema_name})")
        
        if company_id not in self._initialized_companies:
            if await self._ensure_tenant_tables(company_id):
                self._initialized_companies.add(company_id)
        
        async_session_maker = await self._get_async_session_maker()
        
        async with async_session_maker() as session:
            # Устанавливаем search_path для этой сессии.
            # ВАЖНО: после использования сбрасываем search_path обратно в public,
            # чтобы не было утечки схемы при возврате соединения в пул.
            await session.execute(text(f'SET search_path TO "{schema_name}", public'))
            try:
                yield session
            finally:
                try:
                    await session.execute(text('SET search_path TO public'))
                except Exception as e:
                    logger.warning(f"Не удалось сбросить search_path в public для {schema_name}: {e}")

    async def _ensure_tenant_tables(self, company_id: int) -> bool:
        """
        Убедиться, что tenant схема содержит все необходимые таблицы.
        
        Создает отсутствующие таблицы по структуре public схемы без копирования данных.
        """
        schema_name = f"tenant_{company_id}"
        tables_to_clone = [
            "users",
            "services",
            "masters",
            "bookings",
            "clients",
            "posts",
            "timeslots",
            "notifications",
            "settings",
            "broadcasts",
            "blocked_slots",
            "promocodes",
            "promotions",
        ]
        
        try:
            async_session_maker = await self._get_async_session_maker()
            async with async_session_maker() as session:
                result = await session.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = :schema_name"
                    ),
                    {"schema_name": schema_name},
                )
                existing = {row[0] for row in result.fetchall()}
                missing_tables = [table for table in tables_to_clone if table not in existing]
                if not missing_tables:
                    return True
                
                logger.info(
                    f"Tenant {schema_name}: создаем отсутствующие таблицы: {', '.join(missing_tables)}"
                )
                for table_name in missing_tables:
                    await session.execute(
                        text(
                            f'CREATE TABLE IF NOT EXISTS "{schema_name}"."{table_name}" '
                            f'AS SELECT * FROM public."{table_name}" WHERE false'
                        )
                    )
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц tenant схемы {schema_name}: {e}")
            return False


_tenant_service: Optional[TenantService] = None

def get_tenant_service() -> TenantService:
    """
    Получить глобальный экземпляр TenantService.
    
    Returns:
        TenantService - глобальный экземпляр сервиса
    """
    global _tenant_service
    if _tenant_service is None:
        _tenant_service = TenantService()
    return _tenant_service
