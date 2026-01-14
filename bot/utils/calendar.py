"""Утилиты для работы с календарем"""
from datetime import date, timedelta
from calendar import monthrange
from typing import List, Set
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def generate_calendar(
    year: int,
    month: int,
    available_dates: Set[date],
    current_date: date = None
) -> InlineKeyboardMarkup:
    """Генерация календаря на месяц"""
    if current_date is None:
        current_date = date.today()
    
    # Названия месяцев
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    # Дни недели
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    # Получаем первый день месяца и количество дней
    first_day, days_in_month = monthrange(year, month)
    # first_day - это день недели (0 = понедельник, 6 = воскресенье)
    
    buttons = []
    
    # Заголовок с месяцем и годом
    header = f"{month_names[month - 1]} {year}"
    buttons.append([
        InlineKeyboardButton(text=header, callback_data="calendar_header")
    ])
    
    # Дни недели
    buttons.append([
        InlineKeyboardButton(text=day, callback_data="calendar_weekday")
        for day in weekdays
    ])
    
    # Календарная сетка
    current_row = []
    # Пустые ячейки до первого дня месяца
    for _ in range(first_day):
        current_row.append(InlineKeyboardButton(text=" ", callback_data="calendar_empty"))
    
    # Дни месяца
    today = date.today()
    for day in range(1, days_in_month + 1):
        current_date_obj = date(year, month, day)
        
        # Проверяем, доступна ли дата
        is_available = current_date_obj in available_dates
        is_past = current_date_obj < today
        
        if is_past:
            # Прошлые даты - пустые
            current_row.append(
                InlineKeyboardButton(
                    text=" ",
                    callback_data="calendar_empty"
                )
            )
        elif not is_available:
            # Недоступные даты - пустые
            current_row.append(
                InlineKeyboardButton(
                    text=" ",
                    callback_data="calendar_empty"
                )
            )
        else:
            # Доступные даты - кнопкой
            if current_date_obj == today:
                text = f"•{day}•"
            else:
                text = str(day)
            
            current_row.append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"calendar_date_{year}_{month}_{day}"
                )
            )
        
        # Если строка заполнена (7 дней), добавляем её
        if len(current_row) == 7:
            buttons.append(current_row)
            current_row = []
    
    # Заполняем оставшиеся ячейки
    while len(current_row) < 7:
        current_row.append(InlineKeyboardButton(text=" ", callback_data="calendar_empty"))
    if current_row:
        buttons.append(current_row)
    
    # Кнопки навигации
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    
    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1
    
    nav_buttons = [
        InlineKeyboardButton(text="◀️", callback_data=f"calendar_month_{prev_year}_{prev_month}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
        InlineKeyboardButton(text="▶️", callback_data=f"calendar_month_{next_year}_{next_month}"),
    ]
    buttons.append(nav_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_available_dates(start_date: date, end_date: date) -> Set[date]:
    """Получить доступные даты в диапазоне (исключая выходные и прошлые даты)"""
    available = set()
    today = date.today()
    current = start_date if start_date >= today else today
    
    while current <= end_date:
        # Проверяем, что дата не в прошлом и не воскресенье (6 = воскресенье)
        # В салоне красоты работают 7 дней в неделю, но можно добавить проверку
        if current >= today:
            available.add(current)
        current += timedelta(days=1)
    
    return available

