import { useState } from 'react'
import { IconSquare } from '../../components/IconSquare.jsx'
import { PillChip, TypePill } from '../../components/PillChip.jsx'
import { ConfidenceBar } from '../../components/ConfidenceBar.jsx'
import { EditModal } from './EditModal.jsx'

/* ── Evidence chip extraction per type ─────────────────────── */
function getChips(item) {
  const ev = item.evidence_json ?? {}
  const chips = []

  if (item.type === 'genome_match') {
    if (item.listing?.store_name)
      chips.push({ icon: '🏪', label: item.listing.store_name, title: 'اسم المتجر' })
    if (item.listing?.price != null)
      chips.push({ icon: '💰', label: `${item.listing.price.toLocaleString('ar-SA')} ر.س`, title: 'السعر في القائمة' })
    const top = ev.top_candidates?.[0]
    if (top?.similarity != null)
      chips.push({ icon: '🎯', label: `${Math.round(top.similarity * 100)}٪ تطابق`, title: 'نسبة التشابه' })
  }

  if (item.type === 'oracle_pick') {
    if (ev.cluster_label)
      chips.push({ icon: '📍', label: ev.cluster_label, title: 'مجموعة المتجر' })
    if (ev.category_filter)
      chips.push({ icon: '🏷️', label: ev.category_filter, title: 'الفئة' })
    if (ev.candidates_evaluated != null)
      chips.push({ icon: '🏆', label: `${ev.candidates_evaluated} مرشح`, title: 'عدد المرشحين' })
  }

  if (item.type === 'prism_price') {
    if (ev.cluster_label)
      chips.push({ icon: '📍', label: ev.cluster_label, title: 'مجموعة المتجر' })
    if (ev.recommended_price)
      chips.push({ icon: '💰', label: `${ev.recommended_price} ر.س`, title: 'السعر الموصى به' })
    if (ev.cluster_adjustment != null) {
      const pct = (ev.cluster_adjustment * 100).toFixed(1)
      chips.push({ icon: '📊', label: `${pct > 0 ? '+' : ''}${pct}٪`, title: 'تعديل المجموعة' })
    }
  }

  return chips
}

/* ── Confidence value extraction ───────────────────────────── */
function getConfidence(item) {
  const ev = item.evidence_json ?? {}
  if (item.type === 'genome_match') {
    return ev.top_candidates?.[0]?.similarity ?? null
  }
  if (item.type === 'oracle_pick') {
    return ev.ranked_candidates?.[0]?.total_score ?? null
  }
  if (item.type === 'prism_price') {
    // Price fit: abs(cluster_adjustment) → closer to 0 = stronger fit. Map to [0,1].
    const adj = ev.cluster_adjustment
    if (adj == null) return null
    return Math.max(0, 1 - Math.abs(adj))
  }
  return null
}

/* ── Icon type ─────────────────────────────────────────────── */
const ICON_TYPE = { genome_match: 'genome', oracle_pick: 'oracle', prism_price: 'prism' }

/* ── Main card ─────────────────────────────────────────────── */
export function RecCard({ item, reviewer, onAction, actionLoading }) {
  const [showEdit, setShowEdit] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const chips      = getChips(item)
  const confidence = getConfidence(item)

  // Primary headline: product name, falling back to listing title
  const headline =
    item.recommended_product?.canonical_name_ar ??
    item.recommended_product?.canonical_name_en ??
    item.evidence_json?.top_candidates?.[0]?.canonical_name_ar ??
    item.listing?.listing_title_raw ??
    '—'

  // Sub-headline: listing title if different from headline
  const subline =
    item.listing?.listing_title_raw !== headline
      ? item.listing?.listing_title_raw
      : null

  const isLoading = actionLoading != null

  return (
    <>
      <div
        className="card"
        style={{ display: 'flex', flexDirection: 'column', gap: 16 }}
      >
        {/* ── Row 1: type icon + type pill + timestamp ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <IconSquare type={ICON_TYPE[item.type]} />
          <TypePill type={item.type} />
          <span style={{ marginRight: 'auto', fontSize: '0.72rem', color: 'var(--text-3)' }}>
            {item.created_at
              ? new Date(item.created_at).toLocaleString('ar-SA', {
                  month: 'short', day: 'numeric',
                  hour: '2-digit', minute: '2-digit',
                })
              : ''}
          </span>
        </div>

        {/* ── Row 2: headline ── */}
        <div>
          <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-1)', lineHeight: 1.4 }}>
            {headline}
          </div>
          {subline && (
            <div style={{ fontSize: '0.82rem', color: 'var(--text-2)', marginTop: 4 }}>
              {subline}
            </div>
          )}
        </div>

        {/* ── Row 3: evidence chips ── */}
        {chips.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {chips.map((c, i) => (
              <PillChip key={i} icon={c.icon} label={c.label} title={c.title} />
            ))}
          </div>
        )}

        {/* ── Row 4: confidence bar ── */}
        {confidence != null && (
          <ConfidenceBar value={confidence} label="مستوى الثقة" max={1} />
        )}

        {/* ── Row 5: reasoning (collapsible) ── */}
        {item.reasoning_text && (
          <div>
            <button
              onClick={() => setExpanded(v => !v)}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                color: 'var(--text-3)', fontSize: '0.75rem', fontFamily: 'inherit',
                display: 'flex', alignItems: 'center', gap: 4, marginBottom: 6,
              }}
            >
              <span style={{ transform: expanded ? 'rotate(90deg)' : 'rotate(0)', display: 'inline-block', transition: 'transform 0.15s' }}>▶</span>
              {expanded ? 'إخفاء التفاصيل' : 'عرض التفاصيل'}
            </button>
            {expanded && (
              <p
                style={{
                  margin: 0, padding: '10px 14px',
                  borderRadius: 10,
                  background: 'var(--surface-2)',
                  border: '1px solid var(--border-faint)',
                  fontSize: '0.8rem',
                  color: 'var(--text-2)',
                  lineHeight: 1.7,
                }}
              >
                {item.reasoning_text}
              </p>
            )}
          </div>
        )}

        {/* ── Divider ── */}
        <div style={{ height: 1, background: 'var(--border-faint)', margin: '0 -4px' }} />

        {/* ── Row 6: actions ── */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            className="btn-primary"
            disabled={isLoading}
            onClick={() => onAction('approve', item.id)}
          >
            {actionLoading === 'approve' ? '...' : '✓ قبول'}
          </button>
          <button
            className="btn-danger"
            disabled={isLoading}
            onClick={() => onAction('reject', item.id)}
          >
            {actionLoading === 'reject' ? '...' : '✕ رفض'}
          </button>
          <button
            className="btn-ghost"
            disabled={isLoading}
            onClick={() => setShowEdit(true)}
          >
            ✏ تعديل
          </button>
        </div>
      </div>

      {showEdit && (
        <EditModal
          item={item}
          loading={actionLoading === 'edit'}
          onClose={() => setShowEdit(false)}
          onSubmit={val => onAction('edit', item.id, val)}
        />
      )}
    </>
  )
}
