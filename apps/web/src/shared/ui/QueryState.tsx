import { AlertCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export function LoadingState({ compact = false }: { compact?: boolean }) {
  const { t } = useTranslation()
  return (
    <div className={compact ? 'query-state query-state--compact query-state--loading' : 'query-state query-state--loading'} role="status">
      <div className="skeleton-stack" aria-hidden="true">
        <i />
        <i />
        <i />
      </div>
      <span className="visually-hidden">{t('common.loading')}</span>
    </div>
  )
}

export function ErrorState({ message }: { message?: string }) {
  const { t } = useTranslation()
  return (
    <div className="query-state query-state--error" role="alert">
      <AlertCircle size={20} aria-hidden="true" />
      <span>{message || t('common.error')}</span>
    </div>
  )
}
