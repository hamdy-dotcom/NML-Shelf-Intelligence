/** Labeled horizontal confidence/score bar with percentage. */
export function ConfidenceBar({ value, label = 'مستوى الثقة', max = 1 }) {
  const pct = Math.round(Math.min(Math.max(value / max, 0), 1) * 100)

  // Hue: accent red for high confidence, muted for low
  const color = pct >= 80 ? 'var(--accent)' : pct >= 55 ? '#f59e0b' : 'var(--text-3)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-3)', fontWeight: 500 }}>
          {label}
        </span>
        <span style={{ fontSize: '0.8rem', fontWeight: 700, color }}>
          {pct.toLocaleString('ar-SA')}٪
        </span>
      </div>
      <div
        style={{
          height: 6,
          borderRadius: 999,
          background: 'var(--border)',
          overflow: 'hidden',
        }}
      >
        <div
          className="bar-fill"
          style={{
            height: '100%',
            width: `${pct}%`,
            borderRadius: 999,
            background: color,
            transition: 'width 0.4s ease',
          }}
        />
      </div>
    </div>
  )
}
