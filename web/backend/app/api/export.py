"""
Экспорт данных tenant-схемы в CSV.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from typing import Optional

import csv
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.deps.tenant import get_tenant_db
from shared.database.models import Booking, Client, Master, Post, Service, User

router = APIRouter(prefix="/api/export", tags=["export"])


def _csv_response(rows: list[list[object]], filename: str) -> StreamingResponse:
    """Собрать CSV в память и вернуть как StreamingResponse."""
    buffer = StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow(row)
    payload = BytesIO(buffer.getvalue().encode("utf-8-sig"))
    return StreamingResponse(
        payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/bookings")
async def export_bookings(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Экспорт записей в CSV."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут экспортировать данные")

    query = select(Booking)
    if start_date:
        query = query.where(Booking.service_date >= start_date)
    if end_date:
        query = query.where(Booking.service_date <= end_date)
    if status:
        query = query.where(Booking.status == status)
    query = query.order_by(Booking.service_date.desc(), Booking.time.desc())

    bookings = (await db.execute(query)).scalars().all()

    rows: list[list[object]] = [
        [
            "ID",
            "Номер записи",
            "Клиент",
            "Телефон",
            "Услуга",
            "Мастер",
            "Пост",
            "Дата",
            "Время",
            "Длительность",
            "Статус",
            "Сумма",
            "Оплачено",
            "Комментарий",
        ]
    ]

    for booking in bookings:
        client = (
            await db.execute(select(Client).where(Client.id == booking.client_id))
        ).scalar_one_or_none()

        service_name = ""
        if booking.service_id:
            service = (
                await db.execute(select(Service).where(Service.id == booking.service_id))
            ).scalar_one_or_none()
            if service:
                service_name = service.name

        master_name = ""
        if booking.master_id:
            master = (
                await db.execute(select(Master).where(Master.id == booking.master_id))
            ).scalar_one_or_none()
            if master:
                master_name = master.full_name

        post_label = ""
        if booking.post_id:
            post = (
                await db.execute(select(Post).where(Post.id == booking.post_id))
            ).scalar_one_or_none()
            if post:
                post_label = f"Пост №{post.number}"

        rows.append(
            [
                booking.id,
                booking.booking_number or "",
                client.full_name if client else "",
                client.phone if client else "",
                service_name,
                master_name,
                post_label,
                booking.service_date.isoformat() if booking.service_date else "",
                str(booking.time) if booking.time else "",
                booking.duration or 0,
                booking.status or "",
                float(booking.amount) if booking.amount else 0,
                "Да" if booking.is_paid else "Нет",
                booking.comment or "",
            ]
        )

    filename = f"bookings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return _csv_response(rows, filename)


@router.get("/clients")
async def export_clients(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Экспорт клиентов в CSV."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут экспортировать данные")

    clients = (await db.execute(select(Client).order_by(Client.id))).scalars().all()
    rows: list[list[object]] = [
        ["ID", "ФИО", "Телефон", "Визитов", "Сумма", "Дата создания"]
    ]
    for client in clients:
        rows.append(
            [
                client.id,
                client.full_name or "",
                client.phone or "",
                client.total_visits or 0,
                float(client.total_amount or 0),
                client.created_at.isoformat() if client.created_at else "",
            ]
        )

    filename = f"clients_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return _csv_response(rows, filename)


@router.get("/statistics")
async def export_statistics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Экспорт статистики в CSV."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут экспортировать данные")

    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    period_filter = and_(Booking.service_date >= start_date, Booking.service_date <= end_date)

    counts = (
        await db.execute(
            select(
                func.count(case((Booking.status == "new", Booking.id))).label("new"),
                func.count(case((Booking.status == "confirmed", Booking.id))).label("confirmed"),
                func.count(case((Booking.status == "completed", Booking.id))).label("completed"),
                func.count(case((Booking.status == "cancelled", Booking.id))).label("cancelled"),
                func.count(case((Booking.status == "no_show", Booking.id))).label("no_show"),
                func.count(Booking.id).label("total"),
            ).where(period_filter)
        )
    ).first()

    revenue = (
        await db.execute(
            select(
                func.sum(Booking.amount).label("total_revenue"),
                func.sum(case((Booking.is_paid.is_(True), Booking.amount), else_=0)).label(
                    "paid_revenue"
                ),
                func.sum(case((Booking.is_paid.is_(False), Booking.amount), else_=0)).label(
                    "unpaid_revenue"
                ),
                func.avg(Booking.amount).label("average_check"),
            ).where(
                and_(
                    period_filter,
                    Booking.status == "completed",
                )
            )
        )
    ).first()

    top_services = (
        await db.execute(
            select(Service.name, func.count(Booking.id).label("count"))
            .join(Booking, Booking.service_id == Service.id)
            .where(period_filter)
            .group_by(Service.name)
            .order_by(func.count(Booking.id).desc())
            .limit(5)
        )
    ).all()

    top_masters = (
        await db.execute(
            select(Master.full_name, func.count(Booking.id).label("count"))
            .join(Booking, Booking.master_id == Master.id)
            .where(period_filter)
            .group_by(Master.full_name)
            .order_by(func.count(Booking.id).desc())
            .limit(5)
        )
    ).all()

    rows: list[list[object]] = [
        ["Период", f"{start_date} - {end_date}"],
        [],
        ["Записи по статусам"],
        ["Новые", counts.new or 0],
        ["Подтвержденные", counts.confirmed or 0],
        ["Завершенные", counts.completed or 0],
        ["Отмененные", counts.cancelled or 0],
        ["Не явились", counts.no_show or 0],
        ["Всего", counts.total or 0],
        [],
        ["Доходы"],
        ["Общий доход", float(revenue.total_revenue or Decimal("0.00"))],
        ["Оплачено", float(revenue.paid_revenue or Decimal("0.00"))],
        ["Не оплачено", float(revenue.unpaid_revenue or Decimal("0.00"))],
        ["Средний чек", float(revenue.average_check or Decimal("0.00"))],
        [],
        ["Топ услуги"],
    ]
    for service_name, service_count in top_services:
        rows.append([service_name, service_count])
    rows.append([])
    rows.append(["Топ мастера"])
    for master_name, master_count in top_masters:
        rows.append([master_name, master_count])

    filename = f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return _csv_response(rows, filename)


@router.get("/posts")
async def export_posts(
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Экспорт постов в CSV."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут экспортировать данные")

    query = select(Post)
    if is_active is not None:
        query = query.where(Post.is_active == is_active)
    query = query.order_by(Post.number)
    posts = (await db.execute(query)).scalars().all()

    rows: list[list[object]] = [
        ["ID", "Номер", "Название", "Описание", "Активен", "Дата создания"]
    ]
    for post in posts:
        rows.append(
            [
                post.id,
                post.number,
                post.name or "",
                post.description or "",
                "Да" if post.is_active else "Нет",
                post.created_at.isoformat() if post.created_at else "",
            ]
        )

    filename = f"posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return _csv_response(rows, filename)
