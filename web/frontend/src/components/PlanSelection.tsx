/**
 * Компонент выбора тарифного плана
 * 
 * Отображает список тарифных планов в виде карточек
 * Позволяет выбрать один из планов
 */

import React, { useState, useEffect } from 'react'
import { Plan } from '../api/public'
import PlanCard from './PlanCard'
import './PlanCard.css'

interface PlanSelectionProps {
  selectedPlanId: number | null
  onPlanSelect: (planId: number) => void
}

const PlanSelection: React.FC<PlanSelectionProps> = ({
  selectedPlanId,
  onPlanSelect,
}) => {
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Загрузка тарифных планов
  useEffect(() => {
    fetchPlans()
  }, [])

  const fetchPlans = async () => {
    setLoading(true)
    setError(null)

    try {
      // Импортируем API функцию динамически, чтобы избежать проблем с импортами
      const { getPlans } = await import('../api/public')
      const fetchedPlans = await getPlans()
      
      // Убираем бесплатные тарифы (нельзя создать платеж на 0)
      const paidPlans = fetchedPlans.filter(plan => plan.price_monthly > 0)

      // Убираем дубликаты по name и display_order, оставляя только уникальные
      const uniquePlansMap = new Map<string, Plan>()
      paidPlans.forEach(plan => {
        const key = `${plan.name}-${plan.display_order}`
        if (!uniquePlansMap.has(key)) {
          uniquePlansMap.set(key, plan)
        }
      })
      
      // Сортируем планы по display_order
      const sortedPlans = Array.from(uniquePlansMap.values()).sort((a, b) => 
        a.display_order - b.display_order
      )
      
      // Ограничиваем до 3 планов
      const limitedPlans = sortedPlans.slice(0, 3)
      
      setPlans(limitedPlans)
      
      // Автовыбираем первый активный план, если еще ничего не выбрано
      if (limitedPlans.length > 0 && !selectedPlanId) {
        onPlanSelect(limitedPlans[0].id)
      }
    } catch (err: any) {
      console.error('Ошибка загрузки тарифных планов:', err)
      setError(err.message || 'Не удалось загрузить тарифные планы')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="plans-loading">
        <div className="loading-spinner"></div>
        <p>Загрузка тарифных планов...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="plans-error">
        <div className="error-icon">⚠️</div>
        <p>{error}</p>
        <button 
          className="retry-button"
          onClick={fetchPlans}
        >
          Попробовать снова
        </button>
      </div>
    )
  }

  if (plans.length === 0) {
    return (
      <div className="plans-empty">
        <div className="empty-icon">📦</div>
        <p>Нет доступных тарифных планов</p>
        <p className="empty-hint">
          Пожалуйста, свяжитесь с поддержкой
        </p>
      </div>
    )
  }

  // Определяем рекомендуемый план (первый или с особым свойством)
  const featuredPlan = plans.find(plan => plan.display_order === 0) || plans[0]

  return (
    <div className="plan-selection">
      <div className="plan-selection-header">
        <h2 className="selection-title">Выберите тарифный план</h2>
        <p className="selection-description">
          Подберите оптимальный тариф для вашего салона красоты
        </p>
      </div>

      <div className="plans-grid">
        {plans.map((plan) => (
          <PlanCard
            key={plan.id}
            plan={plan}
            isSelected={selectedPlanId === plan.id}
            onSelect={onPlanSelect}
            variant={plan.id === featuredPlan.id ? 'featured' : 'default'}
          />
        ))}
      </div>

      <div className="plan-selection-footer">
        <p className="footer-text">
          💡 Вы можете изменить тарифный план в любой момент в настройках
        </p>
      </div>
    </div>
  )
}

export default PlanSelection

