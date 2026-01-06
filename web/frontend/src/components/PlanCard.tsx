/**
 * Компонент карточки тарифного плана
 * 
 * Отображает информацию о тарифном плане в виде красивой карточки
 */

import React from 'react'
import { Plan } from '../api/public'

interface PlanCardProps {
  plan: Plan
  isSelected?: boolean
  onSelect?: (planId: number) => void
  variant?: 'default' | 'featured'
}

const PlanCard: React.FC<PlanCardProps> = ({
  plan,
  isSelected = false,
  onSelect,
  variant = 'default',
}) => {
  return (
    <div
      className={`plan-card ${variant === 'featured' ? 'featured' : ''} ${
        isSelected ? 'selected' : ''
      }`}
      onClick={() => onSelect && onSelect(plan.id)}
    >
      {variant === 'featured' && (
        <div className="plan-badge">Рекомендуемый</div>
      )}

      <div className="plan-header">
        <h3 className="plan-name">{plan.name}</h3>
        {plan.description && (
          <p className="plan-description">{plan.description}</p>
        )}
      </div>

      <div className="plan-pricing">
        <div className="plan-price-monthly">
          {plan.price_monthly.toLocaleString('ru-RU')} ₽
          <span className="plan-period">/мес</span>
        </div>
        <div className="plan-price-yearly">
          или {plan.price_yearly.toLocaleString('ru-RU')} ₽/год
        </div>
      </div>

      <ul className="plan-features">
        <li className="plan-feature">
          <span className="feature-icon">📋</span>
          <span>До {plan.max_bookings_per_month.toLocaleString('ru-RU')} записей/мес</span>
        </li>
        <li className="plan-feature">
          <span className="feature-icon">👥</span>
          <span>До {plan.max_users.toLocaleString('ru-RU')} пользователей</span>
        </li>
        <li className="plan-feature">
          <span className="feature-icon">👨‍🔧</span>
          <span>До {plan.max_masters.toLocaleString('ru-RU')} мастеров</span>
        </li>
      </ul>

      {onSelect && (
        <button
          className={`plan-button ${variant === 'featured' ? 'featured' : ''} ${
            isSelected ? 'selected' : ''
          }`}
          onClick={() => onSelect(plan.id)}
        >
          {isSelected ? 'Выбрано ✓' : 'Выбрать'}
        </button>
      )}
    </div>
  )
}

export default PlanCard

