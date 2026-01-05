import { useEffect, useState } from 'react'
import './SuccessNotification.css'

interface SuccessNotificationProps {
  message: string
  onClose?: () => void
  duration?: number
}

export function SuccessNotification({ message, onClose, duration = 3000 }: SuccessNotificationProps) {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    console.log('🎨 SuccessNotification: компонент смонтирован, duration =', duration)
    const timer = setTimeout(() => {
      console.log('🎨 SuccessNotification: скрываем уведомление')
      setVisible(false)
      setTimeout(() => {
        console.log('🎨 SuccessNotification: вызываем onClose')
        onClose?.()
      }, 300) // Ждем завершения анимации
    }, duration)

    return () => {
      console.log('🎨 SuccessNotification: очистка таймера')
      clearTimeout(timer)
    }
  }, [duration, onClose])

  console.log('🎨 SuccessNotification: render, visible =', visible)

  if (!visible) {
    console.log('🎨 SuccessNotification: не рендерим, visible = false')
    return null
  }

  console.log('🎨 SuccessNotification: рендерим компонент')
  return (
    <div className="success-notification" style={{ zIndex: 99999 }}>
      <div className="success-notification-content">
        <span className="success-notification-icon">✓</span>
        <span className="success-notification-message">{message}</span>
      </div>
    </div>
  )
}

