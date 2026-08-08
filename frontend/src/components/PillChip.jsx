/** Small pill-shaped chip: icon + label. */
export function PillChip({ icon, label, title }) {
  return (
    <span
      title={title}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: '4px 10px',
        borderRadius: 999,
        background: 'var(--surface-2)',
        border: '1px solid var(--border)',
        fontSize: '0.75rem',
        fontWeight: 500,
        color: 'var(--text-2)',
        whiteSpace: 'nowrap',
        maxWidth: 180,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
      }}
    >
      <span style={{ opacity: 0.75 }}>{icon}</span>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</span>
    </span>
  )
}

/** Accent-coloured pill for status badges. */
export function StatusPill({ status }) {
  const map = {
    pending:  { label: 'قيد المراجعة', bg: 'var(--pending-bg)',  fg: 'var(--pending-fg)' },
    approved: { label: 'مقبول',         bg: 'var(--approved-bg)', fg: 'var(--approved-fg)' },
    rejected: { label: 'مرفوض',         bg: 'var(--rejected-bg)', fg: 'var(--rejected-fg)' },
    edited:   { label: 'معدّل',          bg: 'var(--edited-bg)',   fg: 'var(--edited-fg)' },
  }
  const s = map[status] ?? map.pending
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '3px 9px',
        borderRadius: 999,
        background: s.bg,
        color: s.fg,
        fontSize: '0.72rem',
        fontWeight: 600,
      }}
    >
      {s.label}
    </span>
  )
}

/** Type-labelled pill (genome match / oracle pick / prism price). */
export function TypePill({ type }) {
  const map = {
    genome_match: { label: 'تطابق تلقائي', bg: 'var(--genome-bg)', fg: 'var(--genome-fg)' },
    oracle_pick:  { label: 'اقتراح الرف',   bg: 'var(--oracle-bg)', fg: 'var(--oracle-fg)' },
    prism_price:  { label: 'سعر موصى به',   bg: 'var(--prism-bg)',  fg: 'var(--prism-fg)' },
  }
  const t = map[type] ?? { label: type, bg: 'var(--surface-2)', fg: 'var(--text-2)' }
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '3px 9px',
        borderRadius: 999,
        background: t.bg,
        color: t.fg,
        fontSize: '0.72rem',
        fontWeight: 600,
      }}
    >
      {t.label}
    </span>
  )
}
