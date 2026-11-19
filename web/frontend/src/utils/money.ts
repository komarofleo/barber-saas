/**
 * Форматирование сумм в рублях с копейками (2 знака после запятой).
 */

export function formatMoney(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined || amount === '') {
    return '0,00 ₽'
  }

  const value = typeof amount === 'string' ? Number.parseFloat(amount) : amount
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '0,00 ₽'
  }

  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

/** Только число с копейками, без символа валюты (например для подсказок). */
export function formatMoneyValue(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined || amount === '') {
    return '0,00'
  }

  const value = typeof amount === 'string' ? Number.parseFloat(amount) : amount
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '0,00'
  }

  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}
