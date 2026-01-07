"""
Telegram бот супер-админа.

Этот бот:
- Работает с public схемой (не tenant)
- Управляет всеми компаниями
- Показывает статистику по всем клиентам
- Может деактивировать/активировать компании
- Отправляет уведомления о неоплате
"""
import logging
import os
import sys
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path

# Добавляем путь к web/backend для импорта app
sys.path.insert(0, str(Path(__file__).parent.parent / "web" / "backend"))

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton

from sqlalchemy import text, select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import selectinload

from shared.database.models import Base
from app.models.public_models import Company, Subscription, Payment, Plan, SuperAdmin
from app.database import async_session_maker
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FSM для состояния бота
class SuperAdminState(StatesGroup):
    """Состояния бота супер-админа."""
    MAIN = State()
    COMPANIES = State()
    COMPANY_DETAILS = State()
    SUBSCRIPTIONS = State()
    PAYMENTS = State()
    STATS = State()


# Инициализация бота
bot = Bot(token=os.getenv("SUPER_ADMIN_BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())
router = Router()


# Инициализация FSM (убрана неправильная строка)


@router.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Начало работы с ботом супер-админа.
    """
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь супер-админом
    async with async_session_maker() as session:
        result = await session.execute(
            select(SuperAdmin).where(SuperAdmin.telegram_id == user_id)
        )
        super_admin = result.scalar_one_or_none()
        
        if not super_admin:
            await message.answer(
                "❌ У вас нет прав доступа к боту супер-админа."
            )
            return
        
        # Создаем главное меню с кнопками
        main_menu = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Статистика")],
                [KeyboardButton(text="🏢 Компании")],
                [KeyboardButton(text="💳 Подписки")],
                [KeyboardButton(text="💰 Платежи")],
                [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="❓ Помощь")],
            ],
            resize_keyboard=True,
            input_field_placeholder="Выберите действие..."
        )
        
        await state.set_state(SuperAdminState.MAIN)
        
        await message.answer(
            f"👋 Добро пожаловать, {super_admin.username}!\n\n"
            "🤖 Панель супер-админа AutoService SaaS\n\n"
            "Выберите действие из меню ниже:",
            reply_markup=main_menu
        )


@router.message(F.text == "📊 Статистика")
async def cmd_stats(message: types.Message, state: FSMContext):
    """
    Показать статистику по всем компаниям.
    """
    user_id = message.from_user.id
    
    # Проверяем права супер-админа
    async with async_session_maker() as session:
        result = await session.execute(
            select(SuperAdmin).where(SuperAdmin.telegram_id == user_id)
        )
        super_admin = result.scalar_one_or_none()
        
        if not super_admin:
            await message.answer("❌ У вас нет прав доступа к боту супер-админа.")
            return
        
        # Количество компаний
        companies_count = await session.scalar(
            select(func.count(Company.id)).where(Company.is_active == True)
        ) or 0
        
        # Количество активных подписок
        active_subs = await session.scalar(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        ) or 0
        
        # Количество истекающих подписок (более 7 дней)
        expiring_soon = await session.scalar(
            select(func.count(Subscription.id)).where(
                and_(
                    Subscription.status == "active",
                    Subscription.end_date <= (date.today() + timedelta(days=7))
                )
            )
        ) or 0
        
        # Общая сумма платежей за месяц
        from sqlalchemy import extract
        current_year = datetime.utcnow().year
        current_month = datetime.utcnow().month
        total_revenue = await session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                and_(
                    Payment.status == "succeeded",
                    extract("year", Payment.created_at) == current_year,
                    extract("month", Payment.created_at) == current_month
                )
            )
        ) or Decimal("0.00")
        
        # Количество компаний с истекшей подпиской
        expired_subs = await session.scalar(
            select(func.count(Subscription.id)).where(
                and_(
                    Subscription.status == "active",
                    Subscription.end_date < date.today()
                )
            )
        ) or 0
        
        stats_text = (
            f"📊 **Статистика AutoService SaaS**\n\n"
            f"🏢 **Компании:**\n"
            f"  • Всего компаний: {companies_count}\n"
            f"  • Активных подписок: {active_subs}\n"
            f"  • Истекает скоро (≤7 дней): {expiring_soon}\n"
            f"  • Истекших подписок: {expired_subs}\n\n"
            f"💰 **Платежи (текущий месяц):**\n"
            f"  • Общая выручка: {float(total_revenue):.2f} RUB\n\n"
        )
        
        await message.answer(stats_text, parse_mode="Markdown")


@router.message(F.text == "🏢 Компании")
async def cmd_companies(message: types.Message, state: FSMContext):
    """
    Показать список компаний.
    """
    page = 1
    page_size = 10
    
    async with async_session_maker() as session:
        query = select(Company).options(
            selectinload(Company.subscriptions)
        ).where(Company.is_active == True)
        
        total = await session.scalar(
            select(func.count(Company.id)).where(Company.is_active == True)
        ) or 0
        
        # Пагинация
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Company.created_at.desc())
        
        result = await session.execute(query)
        companies = result.scalars().all()
        
        if not companies:
            await message.answer("📭 Нет активных компаний.")
            return
        
        # Формируем ответ
        response_text = f"📋 **Компании (стр. {page} из {total // page_size + 1}):**\n\n"
        
        for company in companies:
            # Определяем статус подписки
            sub_status = "❌ Нет подписки"
            sub_end_date = None
            days_left = None
            
            # Получаем активную подписку
            active_subscription = None
            if company.subscriptions:
                # Ищем активную подписку
                for sub in company.subscriptions:
                    if sub.status == "active":
                        active_subscription = sub
                        break
            
            if active_subscription:
                days_left = (active_subscription.end_date - date.today()).days
                if days_left > 7:
                    sub_status = "✅ Активна"
                    sub_end_date = active_subscription.end_date.strftime("%d.%m.%Y")
                else:
                    sub_status = "⚠️ Истекает"
                    sub_end_date = active_subscription.end_date.strftime("%d.%m.%Y")
                    if days_left < 0:
                        days_left = -days_left
            
            company_card = (
                f"🏢 **{company.name}**\n"
                f"📧 Email: {company.email}\n"
                f"📱 Телефон: {company.phone or 'Не указан'}\n"
                f"📊 Подписка: {sub_status}\n"
                f"📅 Дата окончания: {sub_end_date or 'Неактивна'}\n"
            )
            
            if days_left is not None and days_left < 0:
                company_card += f"⚠️ Просрочка: {-days_left} дней\n"
            
            response_text += company_card + "\n"
        
        # Пагинация
        if total > page * page_size:
            response_text += f"\n📄 Показано {page * page_size} из {total} компаний\n"
            response_text += f"👉 /next - следующая страница"
        
        # Кнопка возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main")],
        ])
        
        await message.answer(response_text, reply_markup=keyboard, parse_mode="Markdown")
        
        # Сохраняем страницу
        await state.update_data({"companies_page": page})


@router.callback_query(F.data.startswith("company_"))
async def callback_company_details(callback: CallbackQuery, state: FSMContext):
    """
    Показать детали компании.
    """
    company_id = int(callback.data.split("_")[1])
    
    async with async_session_maker() as session:
        company = await session.execute(
            select(Company)
            .options(selectinload(Company.subscription))
            .where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        
        if not company:
            await callback.message.answer("❌ Компания не найдена.")
            await callback.answer()
            return
        
        # Получаем платежи компании
        payments_result = await session.execute(
            select(Payment)
            .where(Payment.company_id == company_id)
            .order_by(Payment.created_at.desc())
            .limit(5)
        )
        payments = payments_result.scalars().all()
        
        # Формируем ответ
        response_text = (
            f"🏢 **{company.name}**\n\n"
            f"📧 Email: {company.email}\n"
            f"📱 Телефон: {company.phone or 'Не указан'}\n\n"
        )
        
        if company.subscription:
            sub = company.subscription
            response_text += (
                f"📊 **Подписка:**\n"
                f"Статус: {sub.status}\n"
                f"План: {sub.plan.name if sub.plan else 'Неизвестно'}\n"
                f"Начало: {sub.start_date.strftime('%d.%m.%Y')}\n"
                f"Окончание: {sub.end_date.strftime('%d.%m.%Y') if sub.end_date else 'Неактивна'}\n"
            )
        else:
            response_text += "📊 **Подписка:** ❌ Неактивна\n"
        
        if payments:
            response_text += "\n💰 **Последние платежи:**\n"
            for payment in payments:
                response_text += f"  • {payment.created_at.strftime('%d.%m.%Y %H:%M')} - {payment.amount:.2f} RUB ({payment.status})\n"
        
        # Кнопки действий
        keyboard_actions = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton("📧 Изменить", callback_data=f"edit_{company.id}"),
                InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{company.id}"),
            ],
            [
                InlineKeyboardButton("🏠 Главное меню", callback_data="main"),
                InlineKeyboardButton("📋 Список", callback_data="companies"),
            ]
        ])
        
        await callback.message.edit_text(response_text, reply_markup=keyboard_actions)
        await callback.answer()


@router.callback_query(F.data == "refresh")
async def callback_refresh(callback: CallbackQuery):
    """
    Обновить данные.
    """
    await callback.answer("🔄 Обновление...")
    
    # Возвращаем к текущему меню
    state_data = await dp.storage.get_data(callback.from_user.id)
    current_state = state_data.get("state", "")
    
    if current_state == "companies":
        # Вызываем команду "Компании"
        cmd = cmd_companies
        message = callback.message
        await cmd(message, await dp.current_state(callback.from_user.id))


@router.callback_query(F.data == "main")
async def callback_main(callback: CallbackQuery):
    """
    Вернуться в главное меню.
    """
    await callback.answer("🏠 Главное меню")
    
    # Показываем главное меню
    cmd = cmd_start
    message = callback.message
    await cmd(message, await dp.current_state(callback.from_user.id))


@router.callback_query(F.data.startswith("next"))
async def callback_next(callback: CallbackQuery, state: FSMContext):
    """
    Следующая страница списка компаний.
    """
    await callback.answer("📄 Следующая страница")
    
    # Увеличиваем страницу
    state_data = await dp.storage.get_data(callback.from_user.id)
    current_page = state_data.get("companies_page", 1)
    next_page = current_page + 1
    
    # Вызываем команду "Компании"
    cmd = cmd_companies
    message = callback.message
    
    # Обновляем страницу
    await state.update_data({"companies_page": next_page})
    await cmd(message, await dp.current_state(callback.from_user.id))


@router.callback_query(F.data.startswith("edit_"))
async def callback_edit_company(callback: CallbackQuery):
    """
    Редактировать компанию.
    """
    company_id = int(callback.data.split("_")[1])
    
    await callback.message.answer(
        "📝 Редактирование компании...\n"
        "⚠️  Функция редактирования пока не реализована.\n"
        "Пожалуйста, используйте SQL напрямую."
    )


@router.message(F.text == "⚠️ Напоминания")
async def cmd_send_expiration_reminders(message: types.Message, state: FSMContext):
    """
    Отправить напоминания компаниям об истекающих подписках.
    """
    async with async_session_maker() as session:
        # Находим компании с истекающей подпиской
        companies = await session.execute(
            select(Company)
            .options(selectinload(Company.subscription))
            .where(
                and_(
                    Company.is_active == True,
                    Company.id == Company.subscription_id
                )
            )
        ).all()
        
        expired_companies = []
        for company in companies:
            if company.subscription:
                sub = company.subscription
                days_left = (sub.end_date - date.today()).days
                
                if days_left <= 7 and days_left >= 0:
                    expired_companies.append(company)
        
        if not expired_companies:
            await message.answer(
                "✅ Нет компаний с истекающей подпиской."
            )
            return
        
        # Отправляем напоминания
        sent_count = 0
        for company in expired_companies:
            if company.admin_telegram_id:
                try:
                    days_left = (company.subscription.end_date - date.today()).days
                    reminder_text = (
                        f"⚠️ **Напоминание для {company.name}**\n\n"
                        f"📅 Подписка истекает через {days_left} дней!\n"
                        f"📅 Дата окончания: {company.subscription.end_date.strftime('%d.%m.%Y')}\n\n"
                        f"Пожалуйста, продлите подписку для продолжения работы сервиса."
                    )
                    
                    await bot.send_message(
                        chat_id=company.admin_telegram_id,
                        text=reminder_text
                    )
                    
                    sent_count += 1
                    logger.info(f"Напоминание отправлено компании {company.id} (Telegram ID: {company.admin_telegram_id})")
                    
                except Exception as e:
                    logger.error(f"Ошибка отправки напоминания компании {company.id}: {e}")
        
        await message.answer(
            f"✅ Напоминания отправлены {sent_count} компаниям."
        )


@router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: types.Message, state: FSMContext):
    """
    Настройки бота супер-админа.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("🔄 Перезапустить бота", callback_data="restart_bot"),
            InlineKeyboardButton("📊 Показать статистику", callback_data="stats"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="main"),
        ]
    ])
    
    await message.answer("⚙️ Функция настроек в разработке...", reply_markup=keyboard)


@router.message(F.text == "💳 Подписки")
async def cmd_subscriptions(message: types.Message, state: FSMContext):
    """
    Показать список подписок.
    """
    async with async_session_maker() as session:
        # Получаем все подписки
        result = await session.execute(
            select(Subscription, Company)
            .join(Company, Subscription.company_id == Company.id)
            .where(Company.is_active == True)
            .order_by(Subscription.end_date.desc())
            .limit(10)
        )
        subscriptions = result.all()
        
        if not subscriptions:
            await message.answer("📋 Подписок не найдено.")
            return
        
        text = "💳 **Список подписок:**\n\n"
        for sub, company in subscriptions:
            status_emoji = "✅" if sub.status == "active" else "❌"
            text += (
                f"{status_emoji} **{company.name}**\n"
                f"  • Статус: {sub.status}\n"
                f"  • Окончание: {sub.end_date}\n"
                f"  • План: {sub.plan_id}\n\n"
            )
        
        await message.answer(text, parse_mode="Markdown")


@router.message(F.text == "💰 Платежи")
async def cmd_payments(message: types.Message, state: FSMContext):
    """
    Показать список платежей.
    """
    async with async_session_maker() as session:
        # Получаем последние платежи
        result = await session.execute(
            select(Payment, Company)
            .join(Company, Payment.company_id == Company.id)
            .order_by(Payment.created_at.desc())
            .limit(10)
        )
        payments = result.all()
        
        if not payments:
            await message.answer("💰 Платежей не найдено.")
            return
        
        text = "💰 **Последние платежи:**\n\n"
        for payment, company in payments:
            status_emoji = "✅" if payment.status == "succeeded" else "❌"
            text += (
                f"{status_emoji} **{company.name}**\n"
                f"  • Сумма: {payment.amount} RUB\n"
                f"  • Статус: {payment.status}\n"
                f"  • Дата: {payment.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            )
        
        await message.answer(text, parse_mode="Markdown")


@router.message(F.text == "❓ Помощь")
async def cmd_help_menu(message: types.Message, state: FSMContext):
    """
    Показать справку по командам меню.
    """
    help_text = (
        "❓ **Справка по командам:**\n\n"
        "📊 **Статистика** - показать статистику по всем компаниям\n\n"
        "🏢 **Компании** - показать список компаний\n\n"
        "💳 **Подписки** - показать список подписок\n\n"
        "💰 **Платежи** - показать список платежей\n\n"
        "⚙️ **Настройки** - настройки бота\n\n"
        "❓ **Помощь** - показать эту справку\n\n"
        "Используйте кнопки меню для навигации."
    )
    
    await message.answer(help_text, parse_mode="Markdown")


@router.callback_query(F.data == "restart_bot")
async def callback_restart_bot(callback: CallbackQuery):
    """
    Перезапустить бота.
    """
    await callback.answer("🔄 Перезапуск...")
    
    # Перезапускаем полинг
    import subprocess
    subprocess.run(["touch", "/tmp/super_admin_bot_restart"], check=True)
    
    await callback.message.answer("✅ Бот перезапущен!")


@router.message(F.command("help"))
async def cmd_help(message: types.Message):
    """
    Показать справку.
    """
    help_text = (
        "📖 **Справка бота супер-админа AutoService SaaS**\n\n"
        "🔹 **Доступ:** Только для супер-администраторов\n\n"
        "📋 **Доступные команды:**\n"
        "📊 Статистика - показать общую статистику\n"
        "🏢 Компании - список всех компаний\n"
        "⚠️ Напоминания - отправить напоминания об истекающих подписках\n"
        "🔧 Настройки - настройки бота\n\n"
        "🏠 Главное меню - вернуться в главное меню\n\n"
        "🔄 Обновить - обновить данные\n\n"
        "❓ Справка - показать эту справку"
    )
    
    await message.answer(help_text)


# Регистрация роутеров
dp.include_router(router)


async def main():
    """
    Главная функция для запуска бота супер-админа.
    """
    logger.info("Запуск бота супер-админа...")
    
    # Инициализируем БД (используем get_async_session_maker из app.database)
    # БД уже инициализирована через миграции, поэтому просто проверяем подключение
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Подключение к БД успешно")
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise
    
    # Удаляем webhook, если есть (используем polling вместо webhook)
    try:
        # Удаляем webhook с drop_pending_updates для очистки очереди
        result = await bot.delete_webhook(drop_pending_updates=True)
        logger.info(f"Webhook удален, используем polling. Результат: {result}")
        
        # Ждем немного, чтобы Telegram обработал удаление webhook
        import asyncio
        await asyncio.sleep(5)  # Увеличиваем задержку
        
        # Проверяем, что webhook действительно удален
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            logger.warning(f"Webhook все еще активен: {webhook_info.url}, пытаемся удалить еще раз...")
            await bot.delete_webhook(drop_pending_updates=True)
            await asyncio.sleep(3)
    except Exception as e:
        logger.warning(f"Не удалось удалить webhook: {e}")
    
    logger.info("Запуск поллинга...")
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            await dp.start_polling(bot, skip_updates=True, allowed_updates=["message", "callback_query"])
            break  # Если успешно запустился, выходим из цикла
        except Exception as e:
            error_str = str(e)
            if "Conflict" in error_str or "terminated by other getUpdates" in error_str:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 10 * retry_count
                    logger.warning(f"Конфликт с другим экземпляром бота. Ждем {wait_time} секунд и пробуем снова (попытка {retry_count}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                    # Удаляем webhook еще раз перед повторной попыткой
                    try:
                        await bot.delete_webhook(drop_pending_updates=True)
                        await asyncio.sleep(2)
                    except:
                        pass
                else:
                    logger.error(f"Не удалось запустить бот после {max_retries} попыток. Возможно, другой экземпляр бота все еще работает.")
                    raise
            else:
                logger.error(f"Ошибка при запуске поллинга: {e}", exc_info=True)
                raise


if __name__ == "__main__":
    import asyncio
    
    load_dotenv()
    
    # Проверяем наличие токена
    if not os.getenv("SUPER_ADMIN_BOT_TOKEN"):
        logger.error("SUPER_ADMIN_BOT_TOKEN не найден в .env!")
        print("Пожалуйста, укажите токен бота супер-админа в .env:")
        exit(1)
    
    logger.info("Запуск бота супер-админа...")
    asyncio.run(main())

