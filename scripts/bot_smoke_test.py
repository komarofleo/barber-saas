#!/usr/bin/env python3
"""Smoke-тест логики ботов без Telegram polling.

Запуск на сервере:
  docker exec -e PYTHONPATH=/app/web/backend:/app -w /app barber_bot python /tmp/bot_smoke_test.py
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import sys
import traceback
from datetime import date
from typing import Any, List

errors: List[str] = []
oks: List[str] = []


def ok(msg: str) -> None:
    oks.append(msg)
    print(f"OK {msg}")


def fail(msg: str, exc: Exception | None = None) -> None:
    text = msg if exc is None else f"{msg}: {type(exc).__name__}: {exc}"
    errors.append(text)
    print(f"FAIL {text}")
    if exc is not None:
        traceback.print_exc()


async def test_imports_company() -> None:
    modules = [
        "bot.main",
        "bot.bot_manager",
        "bot.handlers.client.start",
        "bot.handlers.client.booking",
        "bot.handlers.client.my_bookings",
        "bot.handlers.client.profile",
        "bot.handlers.client.calendar",
        "bot.handlers.admin.menu",
        "bot.handlers.admin.bookings",
        "bot.handlers.admin.bookings_edit",
        "bot.handlers.admin.edit_booking_service_date",
        "bot.handlers.admin.edit_booking_request_date",
        "bot.handlers.master.work_order",
        "bot.handlers.booking_subscription_check",
        "bot.database.crud",
        "bot.states.admin_states",
    ]
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            ok(f"import {module_name}")
        except Exception as exc:
            fail(f"import {module_name}", exc)

    try:
        from bot.states.admin_states import AdminEditBookingStates

        assert hasattr(AdminEditBookingStates, "editing_datetime")
        ok("AdminEditBookingStates.editing_datetime")
    except Exception as exc:
        fail("AdminEditBookingStates.editing_datetime", exc)


async def test_tenant_crud() -> None:
    from datetime import timedelta

    from sqlalchemy import select, text

    from bot.database import crud
    from bot.database.connection import get_session
    from bot.handlers.master import work_order as wo
    from shared.database.models import Master

    company_id = 1
    crud_fns = [
        name
        for name, obj in inspect.getmembers(crud)
        if inspect.iscoroutinefunction(obj) and not name.startswith("_")
    ]
    ok(f"crud async funcs: {len(crud_fns)}")

    async def run_step(label: str, coro_factory):
        async for session in get_session():
            try:
                await session.execute(text(f'SET LOCAL search_path TO "tenant_{company_id}", public'))
                result = await coro_factory(session)
                ok(f"{label} -> {result}")
                return result
            except Exception as exc:
                await session.rollback()
                fail(label, exc)
                return None

    async def _len_call(awaitable):
        value = await awaitable
        return len(value) if hasattr(value, "__len__") else value

    await run_step(
        "get_services",
        lambda s: _len_call(crud.get_services(s, active_only=True, company_id=company_id)),
    )
    await run_step(
        "get_masters",
        lambda s: _len_call(crud.get_masters(s, company_id=company_id)),
    )
    await run_step(
        "get_posts",
        lambda s: _len_call(crud.get_posts(s, company_id=company_id)),
    )

    async def user_step(session):
        user = await crud.get_or_create_user(
            session,
            telegram_id=329621295,
            username="admin_smoke",
            first_name="Smoke",
            last_name="Admin",
            company_id=company_id,
        )
        return f"id={getattr(user, 'id', None)} admin={getattr(user, 'is_admin', None)}"

    user_info = await run_step("get_or_create_user", user_step)

    async def client_step(session):
        user = await crud.get_user_by_telegram_id(session, 329621295, company_id=company_id)
        client = await crud.get_or_create_client(
            session,
            user_id=user.id,
            full_name="Smoke Admin",
            phone="+79991234567",
            company_id=company_id,
        )
        return f"id={getattr(client, 'id', None)}"

    if user_info:
        await run_step("get_or_create_client", client_step)

    await run_step(
        "get_all_bookings",
        lambda s: _len_call(crud.get_all_bookings(s, company_id=company_id, limit=20)),
    )
    await run_step(
        "get_bookings_by_status(new)",
        lambda s: _len_call(crud.get_bookings_by_status(s, "new", company_id=company_id)),
    )

    async def dates_step(session):
        start = date.today()
        return len(await crud.get_available_dates(session, start, start + timedelta(days=14)))

    await run_step("get_available_dates", dates_step)

    async def work_order_step(session):
        result = await session.execute(select(Master).limit(1))
        master = result.scalar_one_or_none()
        if master is None:
            raise RuntimeError("no masters")
        rows = await wo._get_master_work_orders(session, company_id, master.id, date(2026, 11, 19))
        master_bookings = await crud.get_master_bookings_by_date(
            session,
            master_id=master.id,
            booking_date=date(2026, 11, 19),
        )
        return f"{master.full_name}: wo={len(rows)} bookings={len(master_bookings)}"

    await run_step("work_order/master bookings", work_order_step)


async def test_super_admin() -> None:
    try:
        import bot.super_admin_bot as sab

        ok("import bot.super_admin_bot")
        ok(f"super_admin bot token set={bool(getattr(sab.bot, 'token', None))}")
    except Exception as exc:
        fail("import bot.super_admin_bot", exc)
        return

    try:
        from sqlalchemy import func, select

        from app.database import async_session_maker
        from app.models.public_models import Company, Payment, Plan, Subscription, SuperAdmin

        async with async_session_maker() as session:
            admins = (await session.execute(select(SuperAdmin))).scalars().all()
            ok(f"SuperAdmin n={len(admins)} tg={[a.telegram_id for a in admins]}")

            sa = (
                await session.execute(select(SuperAdmin).where(SuperAdmin.telegram_id == 329621295))
            ).scalar_one_or_none()
            if sa:
                ok(f"super_admin access ok username={sa.username}")
            else:
                fail("super_admin telegram_id 329621295 not found")

            total = await session.scalar(select(func.count(Company.id)))
            active = await session.scalar(
                select(func.count(Company.id)).where(Company.is_active.is_(True))
            )
            ok(f"company stats total={total} active={active}")

            plans = (await session.execute(select(Plan))).scalars().all()
            ok(f"plans={len(plans)}")
            subs = (await session.execute(select(Subscription))).scalars().all()
            ok(f"subscriptions={len(subs)}")
            pays = (await session.execute(select(Payment))).scalars().all()
            ok(f"payments={len(pays)}")

            for company in (await session.execute(select(Company))).scalars().all():
                ok(
                    f"company id={company.id} status={company.subscription_status} "
                    f"can_create={company.can_create_bookings}"
                )
    except Exception as exc:
        fail("super_admin DB paths", exc)


async def test_send_probe() -> None:
    """Проверка getMe + sendMessage админу от обоих ботов."""
    import os

    from aiogram import Bot
    from sqlalchemy import select

    from app.database import async_session_maker
    from app.models.public_models import Company

    admin_tg = 329621295
    company_token = os.getenv("BOT_TOKEN")
    sa_token = os.getenv("SUPER_ADMIN_BOT_TOKEN")

    try:
        async with async_session_maker() as session:
            company = (
                await session.execute(select(Company).where(Company.id == 1))
            ).scalar_one_or_none()
            if company and company.telegram_bot_token:
                company_token = company.telegram_bot_token
    except Exception as exc:
        fail("load company token", exc)

    for label, token in (("company", company_token), ("super_admin", sa_token)):
        if not token:
            fail(f"{label}: token missing")
            continue
        bot = Bot(token=token)
        try:
            me = await bot.get_me()
            ok(f"{label} getMe @{me.username}")
            try:
                msg = await bot.send_message(
                    admin_tg, f"Smoke-тест {label} бота OK (@{me.username})"
                )
                ok(f"{label} send_message message_id={msg.message_id}")
            except Exception as send_exc:
                # chat not found = админ ещё не нажал /start у этого бота (не баг кода)
                err_text = str(send_exc).lower()
                if "chat not found" in err_text:
                    ok(
                        f"{label} send_message skipped: chat not found "
                        f"(нужен /start у @{me.username} от tg={admin_tg})"
                    )
                else:
                    fail(f"{label} telegram send", send_exc)
        except Exception as exc:
            fail(f"{label} telegram getMe", exc)
        finally:
            await bot.session.close()


async def main() -> int:
    print("=== COMPANY BOT IMPORTS ===")
    await test_imports_company()
    print("\n=== TENANT CRUD / WORK ORDER ===")
    await test_tenant_crud()
    print("\n=== SUPER ADMIN BOT ===")
    await test_super_admin()
    print("\n=== TELEGRAM SEND PROBE ===")
    await test_send_probe()
    print("\n=== SUMMARY ===")
    print(f"OK={len(oks)} FAIL={len(errors)}")
    for item in errors:
        print(f" - {item}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
