/** Thin segmented progress bar + "N من M" counter for one-at-a-time review. */
export function QueueProgress({ current, total }) {
  if (!total) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-3)', fontWeight: 500 }}>
          مراجعة البنود المعلقة
        </span>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-2)', fontWeight: 600 }}>
          {current.toLocaleString('ar-SA')} من {total.toLocaleString('ar-SA')}
        </span>
      </div>

      {/* Segmented bar */}
      <div style={{ display: 'flex', gap: 3, height: 4 }}>
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: '100%',
              borderRadius: 999,
              background: i < current ? 'var(--accent)' : 'var(--border)',
              transition: 'background 0.2s',
            }}
          />
        ))}
      </div>
    </div>
  )
}
