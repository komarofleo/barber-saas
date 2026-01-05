"""
Сервис для управления tenant схемами (мульти-тенантность).

Этот модуль предоставляет методы для:
- Создания tenant схем в PostgreSQL
- Клонирования таблиц в tenant схемы
- Получения tenant сессий для работы с изолированными данными
"""

import logging
from typing import AsyncGenerator
from textwrap import dedent

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.database import async_session_maker, engine
from app.models.public_models import Company

logger = logging.getLogger(__name__)


class TenantService:
    """
    Сервис для управления tenant схемами.
    
    Предоставляет методы для создания и управления изолированными
    схемами для каждой компании.
    """
    
    def __init__(self, base_engine: AsyncEngine):
        """Инициализация сервиса с базовым engine."""
        self.base_engine = base_engine
        self.tenant_engines: dict[int, AsyncEngine] = {}
        self.tenant_session_makers: dict[int, sessionmaker] = {}
        
        logger.info("TenantService инициализирован")
    
    async def create_tenant_schema(self, company_id: int) -> bool:
        """
        Создать tenant схему в PostgreSQL.
        
        Args:
            company_id: ID компании для создания схемы
        
        Returns:
            True если схема создана успешно, False в противном случае
        
        Example:
            >>> await tenant_service.create_tenant_schema(1)
            >>> # Создана схема tenant_001
        """
        schema_name = f"tenant_{company_id:03d}"
        logger.info(f"Создание tenant схемы: {schema_name}")
        
        try:
            async with self.base_engine.connect() as conn:
                await conn.execute(
                    text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                )
                await conn.commit()
            
            logger.info(f"Tenant схема {schema_name} создана успешно")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания tenant схемы {schema_name}: {e}")
            return False
    
    async def clone_table_to_tenant(
        self,
        company_id: int,
        table_name: str,
        public_schema: str = "public"
    ) -> bool:
        """
        Клонировать таблицу из public схемы в tenant схему.
        
        Args:
            company_id: ID компании
            table_name: Имя таблицы для клонирования
            public_schema: Схема-источник (по умолчанию public)
        
        Returns:
            True если таблица склонирована, False в противном случае
        
        Example:
            >>> await tenant_service.clone_table_to_tenant(1, "users")
            >>> # Таблица public.users скопирована в tenant_001.users
        """
        schema_name = f"tenant_{company_id:03d}"
        logger.info(f"Клонирование таблицы {table_name} в схему {schema_name}")
        
        try:
            async with self.base_engine.connect() as conn:
                # Клонируем структуру таблицы в tenant схему
                sql = dedent(f"""
                    CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} (
                        LIKE {public_schema}.template_{table_name}
                        INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
                    );
                """)
                await conn.execute(text(sql))
                await conn.commit()
            
            logger.info(f"Таблица {table_name} скопирована в {schema_name} успешно")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка клонирования таблицы {table_name} в {schema_name}: {e}")
            return False
    
    async def clone_all_tables_to_tenant(
        self,
        company_id: int
    ) -> bool:
        """
        Клонировать все необходимые таблицы в tenant схему.
        
        Args:
            company_id: ID компании
        
        Returns:
            True если все таблицы склонированы, False если ошибка
        
        Example:
            >>> await tenant_service.clone_all_tables_to_tenant(1)
            >>> # Все таблицы склонированы в tenant_001
        """
        schema_name = f"tenant_{company_id:03d}"
        logger.info(f"Клонирование всех таблиц в схему {schema_name}")
        
        # Список таблиц для клонирования (из public.template_* в tenant_*)
        tables_to_clone = [
            "users",  # template_users -> tenant_001.users
            "clients",
            "masters",
            "bookings",
            "services",
            "posts",
            "promocodes",
            "promotions",
            "notifications",
            "blocked_slots",
            "master_services",
            "settings"
        ]
        
        success_count = 0
        for table_name in tables_to_clone:
            is_cloned = await self.clone_table_to_tenant(company_id, table_name)
            if is_cloned:
                success_count += 1
        
        total_count = len(tables_to_clone)
        logger.info(f"Успешно склонировано {success_count}/{total_count} таблиц")
        
        return success_count == total_count
    
    async def get_tenant_engine(self, company_id: int) -> AsyncEngine:
        """
        Получить или создать engine для tenant схемы.
        
        Args:
            company_id: ID компании
        
        Returns:
            AsyncEngine для tenant схемы
        """
        if company_id not in self.tenant_engines:
            # Создаем новый engine для tenant схемы с search_path
            from app.database import DATABASE_URL
            tenant_database_url = f"{DATABASE_URL}?options=-csearch_path=tenant_{company_id:03d}"
            
            self.tenant_engines[company_id] = create_async_engine(
                tenant_database_url,
                echo=False
            )
            
            logger.info(f"Engine создан для tenant_{company_id:03d}")
        
        return self.tenant_engines[company_id]
    
    async def get_tenant_session_maker(self, company_id: int) -> sessionmaker:
        """
        Получить или создать session maker для tenant схемы.
        
        Args:
            company_id: ID компании
        
        Returns:
            SessionMaker для tenant схемы
        """
        if company_id not in self.tenant_session_makers:
            engine = await self.get_tenant_engine(company_id)
            self.tenant_session_makers[company_id] = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info(f"Session maker создан для tenant_{company_id:03d}")
        
        return self.tenant_session_makers[company_id]
    
    async def get_tenant_session(
        self,
        company_id: int
    ) -> AsyncGenerator[AsyncSession, None, None]:
        """
        Получить сессию для работы с tenant схемой.
        
        Args:
            company_id: ID компании
        
        Yields:
            AsyncSession для tenant схемы
            
        Example:
            >>> async for session in tenant_service.get_tenant_session(1):
            ...     result = await session.execute(select(User))
            ...     users = result.scalars().all()
        """
        session_maker = await self.get_tenant_session_maker(company_id)
        
        async with session_maker() as session:
            yield session
    
    async def initialize_tenant_for_company(
        self,
        company_id: int
    ) -> bool:
        """
        Полностью инициализировать tenant для компании.
        
        Включает:
        - Создание tenant схемы
        - Клонирование всех таблиц
        - Подготовка к использованию
        
        Args:
            company_id: ID компании
        
        Returns:
            True если tenant инициализирован успешно, False в противном случае
        """
        logger.info(f"Инициализация tenant для компании {company_id}")
        
        # 1. Создать tenant схему
        schema_created = await self.create_tenant_schema(company_id)
        
        if not schema_created:
            logger.error(f"Не удалось создать tenant схему для компании {company_id}")
            return False
        
        # 2. Клонировать все таблицы
        tables_cloned = await self.clone_all_tables_to_tenant(company_id)
        
        if not tables_cloned:
            logger.error(f"Не удалось склонировать таблицы для компании {company_id}")
            return False
        
        logger.info(f"Tenant для компании {company_id} инициализирован успешно")
        return True
    
    async def drop_tenant_schema(self, company_id: int) -> bool:
        """
        Удалить tenant схему (опасная операция!).
        
        Args:
            company_id: ID компании
        
        Returns:
            True если схема удалена, False в противном случае
        
        WARNING:
            Эта операция удалит все данные компании!
        """
        schema_name = f"tenant_{company_id:03d}"
        logger.warning(f"Удаление tenant схемы: {schema_name}")
        
        try:
            async with self.base_engine.connect() as conn:
                await conn.execute(
                    text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
                )
                await conn.commit()
            
            # Удаляем кэшированные engine и session maker
            if company_id in self.tenant_engines:
                del self.tenant_engines[company_id]
            
            if company_id in self.tenant_session_makers:
                del self.tenant_session_makers[company_id]
            
            logger.warning(f"Tenant схема {schema_name} удалена")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления tenant схемы {schema_name}: {e}")
            return False


# Создание экземпляра сервиса (singleton)
_tenant_service: Optional[TenantService] = None


def get_tenant_service() -> TenantService:
    """
    Получить или создать экземпляр TenantService.
    
    Returns:
        Экземпляр TenantService
    """
    global _tenant_service
    
    if _tenant_service is None:
        from app.database import engine
        _tenant_service = TenantService(engine)
    
    return _tenant_service


async def initialize_tenant_for_company(company_id: int) -> bool:
    """
    Удобная функция для инициализации tenant компании.
    
    Args:
        company_id: ID компании
    
    Returns:
        True если tenant инициализирован успешно, False в противном случае
    """
    service = get_tenant_service()
    return await service.initialize_tenant_for_company(company_id)


async def get_tenant_session(company_id: int) -> AsyncGenerator[AsyncSession, None, None]:
    """
    Удобная функция для получения tenant сессии.
    
    Args:
        company_id: ID компании
    
    Yields:
        AsyncSession для tenant схемы
    """
    service = get_tenant_service()
    async for session in service.get_tenant_session(company_id):
        yield session


async def create_tenant_schema(company_id: int) -> bool:
    """
    Удобная функция для создания tenant схемы.
    
    Args:
        company_id: ID компании
    
    Returns:
        True если схема создана, False в противном случае
    """
    service = get_tenant_service()
    return await service.create_tenant_schema(company_id)

