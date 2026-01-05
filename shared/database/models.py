"""
SQLAlchemy модели для базы данных AutoService
"""
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, Time, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class User(Base):
    """Пользователи системы"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True, index=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_master = Column(Boolean, default=False, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    client = relationship("Client", back_populates="user", uselist=False, cascade="all, delete-orphan")
    master = relationship("Master", back_populates="user", uselist=False, cascade="all, delete-orphan")
    bookings_created = relationship("Booking", foreign_keys="Booking.created_by", back_populates="creator")
    booking_history = relationship("BookingHistory", back_populates="changed_by_user")
    notifications = relationship("Notification", back_populates="user")
    broadcasts_created = relationship("Broadcast", back_populates="creator")
    blocked_slots_created = relationship("BlockedSlot", back_populates="creator")


class Client(Base):
    """Информация о клиентах"""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    car_brand = Column(String(100), nullable=True)
    car_model = Column(String(100), nullable=True)
    car_number = Column(String(20), nullable=True, index=True)
    total_visits = Column(Integer, default=0, nullable=False)
    total_amount = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="client")
    bookings = relationship("Booking", back_populates="client", cascade="all, delete-orphan")
    history = relationship("ClientHistory", back_populates="client", cascade="all, delete-orphan")


class Master(Base):
    """Мастера автосервиса"""
    __tablename__ = "masters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    telegram_id = Column(BigInteger, nullable=True, index=True)
    specialization = Column(String(100), nullable=True)
    is_universal = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="master")
    services = relationship("MasterService", back_populates="master", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="master")
    blocked_slots = relationship("BlockedSlot", back_populates="master", cascade="all, delete-orphan")
    history = relationship("ClientHistory", back_populates="master")


class Service(Base):
    """Услуги автосервиса"""
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration = Column(Integer, nullable=False)  # в минутах
    price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    master_services = relationship("MasterService", back_populates="service", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="service")
    blocked_slots = relationship("BlockedSlot", back_populates="service", cascade="all, delete-orphan")
    promocodes = relationship("Promocode", back_populates="service", cascade="all, delete-orphan")
    promotions = relationship("Promotion", back_populates="service", cascade="all, delete-orphan")
    history = relationship("ClientHistory", back_populates="service")


class MasterService(Base):
    """Специализация мастеров (many-to-many)"""
    __tablename__ = "master_services"

    id = Column(Integer, primary_key=True, index=True)
    master_id = Column(Integer, ForeignKey("masters.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    master = relationship("Master", back_populates="services")
    service = relationship("Service", back_populates="master_services")

    __table_args__ = (
        UniqueConstraint("master_id", "service_id", name="uq_master_service"),
    )


class Post(Base):
    """Посты/боксы автосервиса"""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    bookings = relationship("Booking", back_populates="post")
    blocked_slots = relationship("BlockedSlot", back_populates="post", cascade="all, delete-orphan")


class Booking(Base):
    """Записи клиентов"""
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_number = Column(String(50), unique=True, nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True)
    master_id = Column(Integer, ForeignKey("masters.id", ondelete="SET NULL"), nullable=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    date = Column(Date, nullable=False, index=True)
    time = Column(Time, nullable=False)
    duration = Column(Integer, nullable=False)  # в минутах
    end_time = Column(Time, nullable=False)

    status = Column(String(50), default="new", nullable=False, index=True)  # new, confirmed, completed, cancelled, no_show, priority

    amount = Column(Numeric(10, 2), nullable=True)
    is_paid = Column(Boolean, default=False, nullable=False)
    payment_method = Column(String(50), nullable=True)  # cash, card, qr

    promocode_id = Column(Integer, ForeignKey("promocodes.id", ondelete="SET NULL"), nullable=True)
    discount_amount = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    comment = Column(Text, nullable=True)
    admin_comment = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="bookings")
    service = relationship("Service", back_populates="bookings")
    master = relationship("Master", back_populates="bookings")
    post = relationship("Post", back_populates="bookings")
    creator = relationship("User", foreign_keys=[created_by], back_populates="bookings_created")
    promocode = relationship("Promocode", back_populates="bookings")
    history = relationship("BookingHistory", back_populates="booking", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="booking")
    timeslots = relationship("Timeslot", back_populates="booking")
    client_history = relationship("ClientHistory", back_populates="booking")

    __table_args__ = (
        Index("idx_bookings_date_time", "date", "time"),
        Index("idx_bookings_date_status", "date", "status"),
    )


class BookingHistory(Base):
    """История изменений записей"""
    __tablename__ = "booking_history"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    changed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    booking = relationship("Booking", back_populates="history")
    changed_by_user = relationship("User", back_populates="booking_history")


class ClientHistory(Base):
    """История обслуживания клиентов"""
    __tablename__ = "client_history"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    master_id = Column(Integer, ForeignKey("masters.id", ondelete="SET NULL"), nullable=True)
    date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    client = relationship("Client", back_populates="history")
    booking = relationship("Booking", back_populates="client_history")
    service = relationship("Service", back_populates="history")
    master = relationship("Master", back_populates="history")


class Timeslot(Base):
    """Временные слоты для быстрого поиска"""
    __tablename__ = "timeslots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    time = Column(Time, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    booking = relationship("Booking", back_populates="timeslots")

    __table_args__ = (
        UniqueConstraint("date", "time", name="uq_timeslot_date_time"),
        Index("idx_timeslots_date_available", "date", "is_available"),
    )


class BlockedSlot(Base):
    """Блокировки (даты, мастера, посты, услуги)"""
    __tablename__ = "blocked_slots"

    id = Column(Integer, primary_key=True, index=True)
    block_type = Column(String(50), nullable=False, index=True)  # full_service, master, post, service

    master_id = Column(Integer, ForeignKey("masters.id", ondelete="CASCADE"), nullable=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=True, index=True)

    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)

    reason = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    master = relationship("Master", back_populates="blocked_slots")
    post = relationship("Post", back_populates="blocked_slots")
    service = relationship("Service", back_populates="blocked_slots")
    creator = relationship("User", back_populates="blocked_slots_created")

    __table_args__ = (
        Index("idx_blocks_dates", "start_date", "end_date"),
    )


class Promocode(Base):
    """Промокоды"""
    __tablename__ = "promocodes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    discount_type = Column(String(20), nullable=False)  # percent, fixed
    discount_value = Column(Numeric(10, 2), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=True)

    min_amount = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    max_uses = Column(Integer, nullable=True)
    current_uses = Column(Integer, default=0, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    service = relationship("Service", back_populates="promocodes")
    bookings = relationship("Booking", back_populates="promocode")

    __table_args__ = (
        Index("idx_promocodes_active_dates", "is_active", "start_date", "end_date"),
    )


class Promotion(Base):
    """Акции на услуги"""
    __tablename__ = "promotions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    discount_type = Column(String(20), nullable=False)  # percent, fixed
    discount_value = Column(Numeric(10, 2), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=True)

    start_date = Column(Date, nullable=True, index=True)
    end_date = Column(Date, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    service = relationship("Service", back_populates="promotions")

    __table_args__ = (
        Index("idx_promotions_dates", "start_date", "end_date"),
    )


class Notification(Base):
    """История уведомлений"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=True, index=True)
    notification_type = Column(String(50), nullable=False, index=True)  # reminder_day, reminder_hour, status_change, etc.
    message = Column(Text, nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")
    booking = relationship("Booking", back_populates="notifications")


class Broadcast(Base):
    """Рассылки"""
    __tablename__ = "broadcasts"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    image_path = Column(String(500), nullable=True)
    target_audience = Column(String(50), nullable=False)  # all, active, new, by_service
    filter_params = Column(JSONB, nullable=True)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, sending, completed, failed

    total_sent = Column(Integer, default=0, nullable=False)
    total_errors = Column(Integer, default=0, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)

    # Relationships
    creator = relationship("User", back_populates="broadcasts_created")


class Setting(Base):
    """Настройки системы"""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

