import { useState } from 'react'
import { useTheme } from './hooks/useTheme.js'
import { ToastHost } from './components/Toast.jsx'
import { LedgerQueue } from './screens/LedgerQueue/index.jsx'
import { SentinelSearch } from './screens/SentinelSearch/index.jsx'
import { OracleShelf } from './screens/OracleShelf/index.jsx'

/* ── NML wordmark ───────────────────────────────────────────── */
function NMLLogo() {
  return (
    <svg width="52" height="22" viewBox="0 0 52 22" fill="none" xmlns="http://www.w3.org/2000/svg">
      <text x="0" y="17" fontFamily="'Noto Kufi Arabic', sans-serif" fontWeight="700" fontSize="18" fill="var(--accent)">NML</text>
    </svg>
  )
}

/* ── Sun / Moon icons ───────────────────────────────────────── */
function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  )
}
function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  )
}

const NAV_TABS = [
  { id: 'ledger',   label: 'قائمة المراجعة' },
  { id: 'oracle',   label: 'ذكاء الرف' },
  { id: 'search',   label: 'البحث' },
  { id: 'dashboard',label: 'لوحة البيانات',  soon: true },
]

export default function App() {
  const { theme, toggle } = useTheme()
  const [screen, setScreen] = useState('ledger')
  const [reviewer, setReviewer] = useState(
    () => localStorage.getItem('nml-reviewer') ?? 'المراجع'
  )

  function handleReviewerChange(v) {
    setReviewer(v)
    localStorage.setItem('nml-reviewer', v)
  }

  return (
    <div style={{ minHeight: '100dvh', background: 'var(--bg)', color: 'var(--text-1)' }}>
      {/* ── Header ── */}
      <header
        style={{
          position: 'sticky', top: 0, zIndex: 40,
          background: 'var(--surface)',
          borderBottom: '1px solid var(--border)',
          padding: '0 16px',
        }}
      >
        <div
          style={{
            maxWidth: 700,
            margin: '0 auto',
            height: 56,
            display: 'flex',
            alignItems: 'center',
            gap: 16,
          }}
        >
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
            <NMLLogo />
            <span
              style={{
                fontSize: '0.7rem',
                fontWeight: 600,
                color: 'var(--text-3)',
                borderRight: '1px solid var(--border)',
                paddingRight: 8,
                lineHeight: 1.3,
              }}
            >
              ذكاء الرف
            </span>
          </div>

          {/* Nav tabs */}
          <nav style={{ display: 'flex', gap: 2, flex: 1, overflow: 'auto', scrollbarWidth: 'none' }}>
            {NAV_TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => !tab.soon && setScreen(tab.id)}
                style={{
                  padding: '6px 12px',
                  borderRadius: 8,
                  border: 'none',
                  background: screen === tab.id ? 'var(--accent-bg)' : 'transparent',
                  color: screen === tab.id
                    ? 'var(--accent)'
                    : tab.soon ? 'var(--text-3)' : 'var(--text-2)',
                  fontWeight: screen === tab.id ? 700 : 500,
                  fontSize: '0.82rem',
                  cursor: tab.soon ? 'default' : 'pointer',
                  whiteSpace: 'nowrap',
                  fontFamily: 'inherit',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                  transition: 'background 0.15s, color 0.15s',
                }}
              >
                {tab.label}
                {tab.soon && (
                  <span
                    style={{
                      fontSize: '0.6rem', padding: '1px 5px', borderRadius: 4,
                      background: 'var(--border)', color: 'var(--text-3)',
                    }}
                  >
                    قريباً
                  </span>
                )}
              </button>
            ))}
          </nav>

          {/* Reviewer input */}
          <input
            value={reviewer}
            onChange={e => handleReviewerChange(e.target.value)}
            placeholder="اسم المراجع"
            title="اسم المراجع — يُسجَّل مع كل إجراء"
            style={{
              width: 100,
              padding: '5px 10px',
              borderRadius: 8,
              border: '1px solid var(--border)',
              background: 'var(--surface-2)',
              color: 'var(--text-2)',
              fontSize: '0.75rem',
              fontFamily: 'inherit',
              textAlign: 'center',
              outline: 'none',
              flexShrink: 0,
            }}
          />

          {/* Theme toggle */}
          <button
            onClick={toggle}
            title={theme === 'dark' ? 'الوضع الفاتح' : 'الوضع الداكن'}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-2)', padding: 6, borderRadius: 8,
              display: 'flex', alignItems: 'center',
              flexShrink: 0,
            }}
          >
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
        </div>
      </header>

      {/* ── Main content ── */}
      <main>
        {screen === 'ledger' && <LedgerQueue reviewer={reviewer} />}
        {screen === 'oracle' && <OracleShelf reviewer={reviewer} />}
        {screen === 'search' && <SentinelSearch />}
      </main>

      <ToastHost />
    </div>
  )
}
