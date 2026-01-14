"""Скрипт для заполнения начальных данными БД (seed data)."""
import asyncio
import sys
import os
from datetime import datetime

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_database():
    """Заполнить БД начальными данными."""
    
    print("🌱 Заполнение БД начальными данными...")
    
    try:
        # Создаем подключение к БД для public схемы
        database_url = (
            f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )
        engine = create_async_engine(database_url, echo=False)
        async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session_maker() as session:
            
            # Проверяем, есть ли уже тарифные планы
            result = await session.execute(text("SELECT COUNT(*) FROM plans"))
            plans_count = result.scalar()
            
            if plans_count > 0:
                print("ℹ️  Тарифные планы уже существуют, пропускаем...")
            else:
                # Создаем тарифные планы
                print("📋 Создание тарифных планов...")
                
                plans = [
                    {
                        'name': 'Starter',
                        'description': 'Начальный тариф для небольших салонов красоты',
                        'price_monthly': 2990.00,
                        'price_yearly': 29900.00,
                        'max_bookings_per_month': 50,
                        'max_users': 5,
                        'max_masters': 3,
                        'max_posts': 5,
                        'max_promotions': 2,
                        'display_order': 1,
                        'is_active': True
                    },
                    {
                        'name': 'Pro',
                        'description': 'Оптимальный тариф для среднего бизнеса',
                        'price_monthly': 5990.00,
                        'price_yearly': 59900.00,
                        'max_bookings_per_month': 200,
                        'max_users': 20,
                        'max_masters': 10,
                        'max_posts': 20,
                        'max_promotions': 10,
                        'display_order': 2,
                        'is_active': True
                    },
                    {
                        'name': 'Business',
                        'description': 'Полный функционал для крупных сетей салонов красоты',
                        'price_monthly': 11990.00,
                        'price_yearly': 119900.00,
                        'max_bookings_per_month': 1000,
                        'max_users': 100,
                        'max_masters': 50,
                        'max_posts': 100,
                        'max_promotions': 50,
                        'display_order': 3,
                        'is_active': True
                    }
                ]
                
                for plan in plans:
                    await session.execute(text("""
                        INSERT INTO plans (
                            name, description, price_monthly, price_yearly,
                            max_bookings_per_month, max_users, max_masters,
                            max_posts, max_promotions, display_order, is_active
                        ) VALUES (
                            :name, :description, :price_monthly, :price_yearly,
                            :max_bookings_per_month, :max_users, :max_masters,
                            :max_posts, :max_promotions, :display_order, :is_active
                        )
                    """), plan)
                    print(f"  ✅ Тариф {plan['name']} создан")
                
                print("🎉 Тарифные планы успешно созданы!")
            
            # Проверяем, есть ли супер-администраторы
            result = await session.execute(text("SELECT COUNT(*) FROM super_admins"))
            admins_count = result.scalar()
            
            if admins_count > 0:
                print("ℹ️  Супер-администраторы уже существуют, пропускаем...")
            else:
                # Создаем супер-администратора
                print("👑 Создание супер-администратора...")
                
                admin_data = {
                    'username': os.getenv('SUPER_ADMIN_USERNAME', 'admin'),
                    'email': os.getenv('SUPER_ADMIN_EMAIL', 'admin@barber-saas.com'),
                    'password_hash': pwd_context.hash(os.getenv('SUPER_ADMIN_PASSWORD', 'admin123')),
                    'is_super_admin': True,
                    'is_active': True
                }
                
                await session.execute(text("""
                    INSERT INTO super_admins (username, email, password_hash, is_super_admin, is_active)
                    VALUES (:username, :email, :password_hash, :is_super_admin, :is_active)
                """), admin_data)
                
                print(f"  ✅ Супер-администратор {admin_data['username']} создан")
                print(f"  📧 Email: {admin_data['email']}")
                print(f"  🔐 Пароль: {os.getenv('SUPER_ADMIN_PASSWORD', 'admin123')}")
                print("  ⚠️  Не забудьте изменить пароль после первого входа!")
            
            # Фиксируем изменения
            await session.commit()
            print("\n✅ Начальные данные успешно добавлены!")
        
        await engine.dispose()
            
    except Exception as e:
        print(f"❌ Ошибка при заполнении БД: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(seed_database())

