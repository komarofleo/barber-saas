import { useState } from 'react'
import './Calendar.css'

interface CalendarProps {
  selectedDate: Date | null
  onDateSelect: (date: Date) => void
  minDate?: Date
  maxDate?: Date
}

function Calendar({ selectedDate, onDateSelect, minDate, maxDate }: CalendarProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  
  const today = new Date()
  const year = currentMonth.getFullYear()
  const month = currentMonth.getMonth()
  
  const firstDayOfMonth = new Date(year, month, 1)
  const lastDayOfMonth = new Date(year, month + 1, 0)
  const firstDayWeek = firstDayOfMonth.getDay()
  const daysInMonth = lastDayOfMonth.getDate()
  
  const monthNames = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
  ]
  
  const weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
  
  const prevMonth = () => {
    setCurrentMonth(new Date(year, month - 1, 1))
  }
  
  const nextMonth = () => {
    setCurrentMonth(new Date(year, month + 1, 1))
  }
  
  const isDateDisabled = (date: Date): boolean => {
    if (minDate && date < minDate) return true
    if (maxDate && date > maxDate) return true
    return false
  }
  
  const isDateSelected = (date: Date): boolean => {
    if (!selectedDate) return false
    return (
      date.getDate() === selectedDate.getDate() &&
      date.getMonth() === selectedDate.getMonth() &&
      date.getFullYear() === selectedDate.getFullYear()
    )
  }
  
  const isToday = (date: Date): boolean => {
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    )
  }
  
  const handleDateClick = (day: number) => {
    const date = new Date(year, month, day)
    if (!isDateDisabled(date)) {
      onDateSelect(date)
    }
  }
  
  const days = []
  const daysFromPrevMonth = firstDayWeek === 0 ? 6 : firstDayWeek - 1
  
  // Дни предыдущего месяца
  const prevMonthLastDay = new Date(year, month, 0).getDate()
  for (let i = daysFromPrevMonth - 1; i >= 0; i--) {
    const day = prevMonthLastDay - i
    const date = new Date(year, month - 1, day)
    days.push(
      <div
        key={`prev-${day}`}
        className="calendar-day calendar-day-other"
      >
        {day}
      </div>
    )
  }
  
  // Дни текущего месяца
  for (let day = 1; day <= daysInMonth; day++) {
    const date = new Date(year, month, day)
    const disabled = isDateDisabled(date)
    const selected = isDateSelected(date)
    const todayClass = isToday(date) ? 'calendar-day-today' : ''
    
    days.push(
      <div
        key={day}
        className={`calendar-day ${todayClass} ${selected ? 'calendar-day-selected' : ''} ${disabled ? 'calendar-day-disabled' : ''}`}
        onClick={() => !disabled && handleDateClick(day)}
      >
        {day}
      </div>
    )
  }
  
  // Дни следующего месяца для заполнения сетки
  const totalCells = days.length
  const remainingCells = 42 - totalCells // 6 недель * 7 дней
  for (let day = 1; day <= remainingCells; day++) {
    days.push(
      <div
        key={`next-${day}`}
        className="calendar-day calendar-day-other"
      >
        {day}
      </div>
    )
  }
  
  return (
    <div className="calendar">
      <div className="calendar-header">
        <button onClick={prevMonth} className="calendar-nav-btn">‹</button>
        <h3>{monthNames[month]} {year}</h3>
        <button onClick={nextMonth} className="calendar-nav-btn">›</button>
      </div>
      <div className="calendar-weekdays">
        {weekDays.map((day) => (
          <div key={day} className="calendar-weekday">{day}</div>
        ))}
      </div>
      <div className="calendar-days">
        {days}
      </div>
    </div>
  )
}

export default Calendar









