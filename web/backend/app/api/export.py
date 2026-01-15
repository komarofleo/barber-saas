from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import Optional
from datetime import date, datetime
from io import BytesIO
import csv

from app.deps.tenant import get_tenant_db
from .auth import get_current_user
from shared.database.models import User, Booking, Client, Service, Master, Post

router = APIRouter(prefix="/api/export", tags=["export"])

@router.get("/bookings")
async def export_bookings(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Экспорт записей в CSV"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут экспортировать данные")
    
    query = select(Booking)
    
    if start_date:
        query = query.where(Booking.date >= start_date)
    if end_date:
        query = query.where(Booking.date <= end_date)
    if status:
        query = query.where(Booking.status == status)
    
    query = query.order_by(Booking.date.desc(), Booking.time.desc())
    
    result = await db.execute(query)
    bookings = result.scalars().all()
    
    # Создаем CSV в памяти
    output = BytesIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow([
        'ID', 'Номер записи', 'Клиент', 'Телефон', 'Услуга', 'Мастер', 'Пост',
        'Дата', 'Время', 'Длительность', 'Статус', 'Сумма', 'Оплачено', 'Комментарий'
    ])
    
    # Данные
    for booking in bookings:
        # Загружаем связанные данные
        client_result = await db.execute(select(Client).where(Client.id == booking.client_id))
        client = client_result.scalar_one_or_none()
        
        service_name = None
        if booking.service_id:
            service_result = await db.execute(select(Service).where(Service.id == booking.service_id))
            service = service_result.scalar_one_or_none()
            if service:
                service_name = service.name
        
        master_name = None
        if booking.master_id:
            master_result = await db.execute(select(Master).where(Master.id == booking.master_id))
            master = master_result.scalar_one_or_none()
            if master:
                master_name = master.full_name
        
        post_number = None
        if booking.post_id:
            post_result = await db.execute(select(Post).where(Post.id == booking.post_id))
            post = post_result.scalar_one_or_none()
            if post:
                post_number = post.number
        
        writer.writerow([
            booking.id,
            booking.booking_number or '',
            client.full_name if client else '',
            client.phone if client else '',
            service_name or '',
            master_name or '',
            f'Пост №{post_number}' if post_number else '',
            booking.date.isoformat() if booking.date else '',
            str(booking.time) if booking.time else '',
            booking.duration or 0,
            booking.status or '',
            float(booking.amount) if booking.amount else 0,
            'Да' if booking.is_paid else 'Нет',
            booking.comment or '',
        ])
    
    output.seek(0)
    
    filename = f"bookings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/clients")
async def export_clients(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Экспорт клиентов в CSV"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут экспортировать данные")
    
    result = await db.execute(select(Client).order_by(Client.id))
    clients = result.scalars().all()
    
    output = BytesIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'ФИО', 'Телефон', 'Дата создания'])
    
    for client in clients:
        writer.writerow([
            client.id,
            client.full_name or '',
            client.phone or '',
            client.email or '',
            f"{client.car_brand or ''} {client.car_model or ''}".strip(),
            client.created_at.isoformat() if client.created_at else '',
        ])
    
    output.seek(0)
    
    filename = f"clients_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/statistics")
async def export_statistics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Экспорт статистики в CSV"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут экспортировать данные")
    
    from datetime import timedelta
    from sqlalchemy import func, case
    from decimal import Decimal
    
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()
    
    # Вычисляем статистику напрямую
    from shared.database.models import Booking as BookingModel
    
    booking_counts_result = await db.execute(
        select(
            func.count(case((BookingModel.status == 'new', BookingModel.id))).label('new'),
            func.count(case((BookingModel.status == 'confirmed', BookingModel.id))).label('confirmed'),
            func.count(case((BookingModel.status == 'completed', BookingModel.id))).label('completed'),
            func.count(case((BookingModel.status == 'cancelled', BookingModel.id))).label('cancelled'),
            func.count(case((BookingModel.status == 'no_show', BookingModel.id))).label('no_show'),
            func.count(BookingModel.id).label('total')
        ).where(
            and_(BookingModel.date >= start_date, BookingModel.date <= end_date)
        )
    )
    counts = booking_counts_result.first()
    
    revenue_result = await db.execute(
        select(
            func.sum(BookingModel.amount).label('total_revenue'),
            func.sum(case((BookingModel.is_paid == True, BookingModel.amount), else_=0)).label('paid_revenue'),
            func.sum(case((BookingModel.is_paid == False, BookingModel.amount), else_=0)).label('unpaid_revenue'),
            func.avg(BookingModel.amount).label('average_check')
        ).where(
            and_(
                BookingModel.date >= start_date,
                BookingModel.date <= end_date,
                BookingModel.status == 'completed'
            )
        )
    )
    revenue = revenue_result.first()
    
    # Топ услуги
    top_services_result = await db.execute(
        select(
            Service.name,
            func.count(BookingModel.id).label('count')
        ).join(BookingModel, BookingModel.service_id == Service.id).where(
            and_(BookingModel.date >= start_date, BookingModel.date <= end_date)
        ).group_by(Service.name).order_by(func.count(BookingModel.id).desc()).limit(5)
    )
    top_services = [(r.name, r.count) for r in top_services_result.all()]
    
    # Топ мастера
    top_masters_result = await db.execute(
        select(
            Master.full_name,
            func.count(BookingModel.id).label('count')
        ).join(BookingModel, BookingModel.master_id == Master.id).where(
            and_(BookingModel.date >= start_date, BookingModel.date <= end_date)
        ).group_by(Master.full_name).order_by(func.count(BookingModel.id).desc()).limit(5)
    )
    top_masters = [(r.full_name, r.count) for r in top_masters_result.all()]
    
    output = BytesIO()
    writer = csv.writer(output)
    
    writer.writerow(['Период', f'{start_date} - {end_date}'])
    writer.writerow([])
    writer.writerow(['Записи по статусам'])
    writer.writerow(['Новые', counts.new or 0])
    writer.writerow(['Подтвержденные', counts.confirmed or 0])
    writer.writerow(['Завершенные', counts.completed or 0])
    writer.writerow(['Отмененные', counts.cancelled or 0])
    writer.writerow(['Не явились', counts.no_show or 0])
    writer.writerow(['Всего', counts.total or 0])
    writer.writerow([])
    writer.writerow(['Доходы'])
    writer.writerow(['Общий доход', float(revenue.total_revenue or Decimal('0.00'))])
    writer.writerow(['Оплачено', float(revenue.paid_revenue or Decimal('0.00'))])
    writer.writerow(['Не оплачено', float(revenue.unpaid_revenue or Decimal('0.00'))])
    writer.writerow(['Средний чек', float(revenue.average_check or Decimal('0.00'))])
    writer.writerow([])
    writer.writerow(['Топ услуги'])
    for service_name, service_count in top_services:
        writer.writerow([service_name, service_count])
    writer.writerow([])
    writer.writerow(['Топ мастера'])
    for master_name, master_count in top_masters:
        writer.writerow([master_name, master_count])
    
    output.seek(0)
    
    filename = f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/posts")
async def export_posts(
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Экспорт постов в CSV"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут экспортировать данные")
    
    query = select(Post)
    
    if is_active is not None:
        query = query.where(Post.is_active == is_active)
    
    query = query.order_by(Post.number)
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    output = BytesIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Номер', 'Название', 'Описание', 'Активен', 'Дата создания'])
    
    for post in posts:
        writer.writerow([
            post.id,
            post.number,
            post.name or '',
            post.description or '',
            'Да' if post.is_active else 'Нет',
            post.created_at.isoformat() if post.created_at else '',
        ])
    
    output.seek(0)
    
    filename = f"posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

