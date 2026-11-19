#!/usr/bin/env python3
"""Проверка create_booking (путь бота) без Telegram polling."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta

from sqlalchemy import text


async def main() -> int:
    from bot.database import crud
    from bot.database.connection import get_session

    company_id = 1
    async for session in get_session():
        await session.execute(text(f'SET LOCAL search_path TO "tenant_{company_id}", public'))
        client = (
            await session.execute(text("SELECT id FROM clients ORDER BY id LIMIT 1"))
        ).fetchone()
        service = (
            await session.execute(
                text("SELECT id, duration, price FROM services WHERE is_active ORDER BY id LIMIT 1")
            )
        ).fetchone()
        user = (await session.execute(text("SELECT id FROM users ORDER BY id LIMIT 1"))).fetchone()
        if not client or not service or not user:
            print("FAIL missing fixtures", client, service, user)
            return 1

        booking_date = date.today() + timedelta(days=3)
        booking_time = time(11, 0)
        end = (datetime.combine(date.min, booking_time) + timedelta(minutes=int(service[1]))).time()
        booking = await crud.create_booking(
            session,
            client_id=client[0],
            service_id=service[0],
            booking_date=booking_date,
            booking_time=booking_time,
            duration=int(service[1]),
            end_time=end,
            created_by=user[0],
            company_id=company_id,
            amount=float(service[2]) if service[2] is not None else None,
        )
        print(
            f"OK booking id={booking.id} number={booking.booking_number} "
            f"is_paid={booking.is_paid} amount={booking.amount}"
        )
        await session.execute(text("DELETE FROM bookings WHERE id = :id"), {"id": booking.id})
        await session.commit()
        print("OK cleaned")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
