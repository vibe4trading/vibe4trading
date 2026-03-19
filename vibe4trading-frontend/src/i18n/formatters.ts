import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

export function formatDate(date: Date | string | number, locale: string): string {
  const d = date instanceof Date ? date : new Date(date);
  
  if (locale === 'zh') {
    return new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }).format(d);
  }
  
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(d);
}

export function formatNumber(num: number, locale: string): string {
  return new Intl.NumberFormat(locale).format(num);
}

export function formatCurrency(
  amount: number,
  locale: string,
  currency: string = 'USD'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
  }).format(amount);
}

export function useFormatDate() {
  const { i18n } = useTranslation();
  
  return useCallback(
    (date: Date | string | number) => formatDate(date, i18n.language),
    [i18n.language]
  );
}

export function useFormatNumber() {
  const { i18n } = useTranslation();
  
  return useCallback(
    (num: number) => formatNumber(num, i18n.language),
    [i18n.language]
  );
}

export function useFormatCurrency() {
  const { i18n } = useTranslation();
  
  return useCallback(
    (amount: number, currency: string = 'USD') =>
      formatCurrency(amount, i18n.language, currency),
    [i18n.language]
  );
}
