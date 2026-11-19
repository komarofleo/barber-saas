#!/usr/bin/env python3
"""Выставить DEFAULT is_paid/discount_amount во всех tenant_*.bookings.

Запуск на сервере:
  docker exec -e PYTHONPATH=/app -w /app --env-file /opt/barber/.env barber_web \
    python scripts/ensure_bookings_defaults.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.database import async_session_maker


SQL = """
DO $$
DECLARE
    sch text;
BEGIN
    FOR sch IN
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name LIKE 'tenant_%'
    LOOP
        IF EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = sch AND table_name = 'bookings'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.bookings ALTER COLUMN is_paid SET DEFAULT false',
                sch
            );
            EXECUTE format(
                'ALTER TABLE %I.bookings ALTER COLUMN discount_amount SET DEFAULT 0',
                sch
            );
            EXECUTE format(
                'UPDATE %I.bookings SET is_paid = false WHERE is_paid IS NULL',
                sch
            );
            EXECUTE format(
                'UPDATE %I.bookings SET discount_amount = 0 WHERE discount_amount IS NULL',
                sch
            );
            RAISE NOTICE 'defaults applied for %.bookings', sch;
        END IF;
    END LOOP;
END $$;
"""


async def main() -> None:
    async with async_session_maker() as session:
        await session.execute(text(SQL))
        await session.commit()
    print("OK: defaults applied for all tenant_*.bookings")


if __name__ == "__main__":
    asyncio.run(main())
