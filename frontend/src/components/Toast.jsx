import { useEffect, useState } from 'react'

let _setToast = null
export function toast(message, kind = 'success') {
  _setToast?.({ message, kind, id: Date.now() })
}

const ICONS = {
  success: '✓',
  error:   '✕',
  info:    'ℹ',
}
const COLORS = {
  success: 'var(--approved-fg)',
  error:   'var(--rejected-fg)',
  info:    'var(--text-2)',
}

export function ToastHost() {
  const [item, setItem] = useState(null)

  useEffect(() => {
    _setToast = setItem
    return () => { _setToast = null }
  }, [])

  useEffect(() => {
    if (!item) return
    const t = setTimeout(() => setItem(null), 3000)
    return () => clearTimeout(t)
  }, [item])

  if (!item) return null

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 100,
      }}
    >
      <div className="toast">
        <span style={{ color: COLORS[item.kind], fontWeight: 700 }}>
          {ICONS[item.kind]}
        </span>
        {item.message}
      </div>
    </div>
  )
}
