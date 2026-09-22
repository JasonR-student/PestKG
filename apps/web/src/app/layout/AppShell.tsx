import { useQuery } from '@tanstack/react-query'
import {
  BookOpen,
  Download,
  GitCompareArrows,
  Languages,
  LayoutDashboard,
  Menu,
  Network,
  Search,
  X,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router-dom'

import { api } from '../../shared/api/client'
import { useRelease } from '../release/useRelease'
import { GlobalSearch } from './GlobalSearch'
import { ReleaseSelector } from './ReleaseSelector'

const navigation = [
  { to: '/', key: 'overview', icon: LayoutDashboard, end: true },
  { to: '/explore', key: 'explore', icon: Search },
  { to: '/compare', key: 'compare', icon: GitCompareArrows },
  { to: '/downloads', key: 'downloads', icon: Download },
  { to: '/methods', key: 'methods', icon: BookOpen },
]

export function AppShell({ children }: { children: ReactNode }) {
  const { t, i18n } = useTranslation()
  const [menuOpen, setMenuOpen] = useState(false)
  const { releaseId, release, buildUrl } = useRelease()
  const overview = useQuery({
    queryKey: ['overview', releaseId],
    queryFn: ({ signal }) => api.overview(releaseId, signal),
    enabled: Boolean(releaseId),
  })

  const changeLanguage = async (language: 'zh' | 'en') => {
    window.localStorage.setItem('pestkg-language', language)
    await i18n.changeLanguage(language)
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside className={menuOpen ? 'sidebar sidebar--open' : 'sidebar'}>
        <div className="brand-block">
          <div className="brand-mark" aria-hidden="true">
            <Network size={22} />
          </div>
          <div>
            <strong>{t('brandShort')}</strong>
            <span>{t('brand')}</span>
          </div>
          <button
            type="button"
            className="icon-button sidebar-close"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <nav className="primary-nav" aria-label="Primary">
          {navigation.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.key}
                to={buildUrl(item.to)}
                end={item.end}
                onClick={() => setMenuOpen(false)}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{t(`nav.${item.key}`)}</span>
              </NavLink>
            )
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="release-status">
            <span className="status-dot" aria-hidden="true" />
            <span>
              <small>{t('common.release')}</small>
              <strong>{release?.release_id ?? overview.data?.data.version ?? '—'}</strong>
            </span>
          </div>
          <div className="language-control" aria-label="Language">
            <Languages size={16} aria-hidden="true" />
            <button
              type="button"
              className={i18n.language.startsWith('zh') ? 'is-active' : ''}
              onClick={() => void changeLanguage('zh')}
            >
              中
            </button>
            <button
              type="button"
              className={i18n.language.startsWith('en') ? 'is-active' : ''}
              onClick={() => void changeLanguage('en')}
            >
              EN
            </button>
          </div>
        </div>
      </aside>

      {menuOpen ? (
        <button
          type="button"
          className="sidebar-scrim"
          aria-label="Close menu"
          onClick={() => setMenuOpen(false)}
        />
      ) : null}

      <div className="app-main">
        <div className="topbar">
          <button
            type="button"
            className="icon-button mobile-menu-button"
            aria-label="Open menu"
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={20} />
          </button>
          <GlobalSearch />
          <div className="topbar-context">
            <span className="data-mode">
              {overview.data?.data.mode === 'full'
                ? t('common.fullMode')
                : t('common.sampleMode')}
            </span>
            <ReleaseSelector />
          </div>
        </div>
        <main id="main-content" className="main-content">
          {children}
        </main>
      </div>
    </div>
  )
}
