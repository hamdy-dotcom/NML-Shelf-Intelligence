import { useEffect, useRef, useState } from 'react'
import { sentinelApi } from '../../api/ledger.js'
import { ConfidenceBar } from '../../components/ConfidenceBar.jsx'
import { ProductDetail } from './ProductDetail.jsx'

/* ── Search icon ───────────────────────────────────────────── */
function SearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

function ClearIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

function ChevronIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

/* ── Match quality badge ───────────────────────────────────── */
const QUALITY_MAP = {
  exact:      { label: 'تطابق تام',    bg: 'var(--approved-bg)', fg: 'var(--approved-fg)' },
  high:       { label: 'ثقة عالية',    bg: 'var(--approved-bg)', fg: 'var(--approved-fg)' },
  best_guess: { label: 'أفضل تخمين',   bg: 'var(--pending-bg)',  fg: 'var(--pending-fg)' },
  low:        { label: 'ثقة منخفضة',   bg: 'var(--rejected-bg)', fg: 'var(--rejected-fg)' },
}

function QualityBadge({ quality }) {
  const q = QUALITY_MAP[quality] ?? QUALITY_MAP.best_guess
  return (
    <span
      style={{
        padding: '2px 8px', borderRadius: 999,
        background: q.bg, color: q.fg,
        fontSize: '0.68rem', fontWeight: 600,
        flexShrink: 0,
      }}
    >
      {q.label}
    </span>
  )
}

/* ── Individual result card (clickable) ────────────────────── */
function ResultCard({ result, onClick }) {
  const { canonical_name_ar, canonical_name_en, category, similarity,
          match_quality, store_count, listing_count, price_range, resolved } = result

  const priceLabel = price_range
    ? price_range.min === price_range.max
      ? `${price_range.min.toFixed(2)} ر.س`
      : `${price_range.min.toFixed(2)} – ${price_range.max.toFixed(2)} ر.س`
    : null

  return (
    <div
      className="card"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && onClick()}
      style={{
        display: 'flex', flexDirection: 'column', gap: 12,
        cursor: 'pointer',
        transition: 'box-shadow 0.15s, border-color 0.15s',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = 'var(--accent)'
        e.currentTarget.style.boxShadow   = '0 0 0 1px var(--accent)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = ''
        e.currentTarget.style.boxShadow   = ''
      }}
    >
      {/* Row 1: name + quality badge + chevron */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-1)', lineHeight: 1.4 }}>
            {canonical_name_ar ?? canonical_name_en ?? '—'}
          </div>
          {canonical_name_en && canonical_name_ar && (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-3)', marginTop: 2, direction: 'ltr', textAlign: 'right' }}>
              {canonical_name_en}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          <QualityBadge quality={match_quality} />
          <span style={{ color: 'var(--text-3)' }}><ChevronIcon /></span>
        </div>
      </div>

      {/* Row 2: meta chips */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {listing_count != null && (
          <span className="label">🏷️ {listing_count.toLocaleString('ar-SA')} قائمة</span>
        )}
        {store_count != null && (
          <span className="label">🏪 {store_count.toLocaleString('ar-SA')} متجر</span>
        )}
        {priceLabel && (
          <span className="label">💰 {priceLabel}</span>
        )}
        {category && (
          <span className="label">🏷 {category}</span>
        )}
        {!resolved && (
          <span className="label" style={{ color: 'var(--pending-fg)' }}>غير محلول</span>
        )}
      </div>

      {/* Row 3: confidence bar */}
      {similarity != null && (
        <ConfidenceBar value={similarity} label="تشابه البحث" max={1} />
      )}
    </div>
  )
}

/* ── Empty / hint states ───────────────────────────────────── */
function HintState() {
  return (
    <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-3)' }}>
      <div style={{ fontSize: 36, marginBottom: 12 }}>🔍</div>
      <p style={{ margin: 0, fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-2)' }}>
        ابحث عن منتج
      </p>
      <p style={{ margin: '6px 0 0', fontSize: '0.78rem' }}>
        أدخل اسم المنتج أو الفئة للبحث في قاعدة بيانات NML
      </p>
    </div>
  )
}

function EmptyState({ query }) {
  return (
    <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-3)' }}>
      <div style={{ fontSize: 36, marginBottom: 12 }}>📭</div>
      <p style={{ margin: 0, fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-2)' }}>
        لا نتائج لـ "{query}"
      </p>
      <p style={{ margin: '6px 0 0', fontSize: '0.78rem' }}>
        جرّب كلمة مختلفة أو تحقق من قاعدة بيانات المنتجات
      </p>
    </div>
  )
}

/* ── Main screen ───────────────────────────────────────────── */
export function SentinelSearch() {
  const [query, setQuery]         = useState('')
  const [results, setResults]     = useState(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)
  const [selectedId, setSelected] = useState(null)   // product_id of open detail
  const inputRef                  = useRef(null)
  const debounceRef               = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  function runSearch(q) {
    if (!q.trim()) { setResults(null); setError(null); return }
    setLoading(true)
    setError(null)
    sentinelApi.search(q.trim(), 10)
      .then(data => { setResults(data.results ?? []); setLoading(false) })
      .catch(err  => { setError(err.message ?? 'تعذّر الاتصال بالخادم'); setLoading(false) })
  }

  function handleInput(v) {
    setQuery(v)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => runSearch(v), 350)
  }

  function handleClear() {
    setQuery('')
    setResults(null)
    setError(null)
    inputRef.current?.focus()
  }

  // If a product detail is open, render it full-screen (fixed overlay)
  if (selectedId) {
    return (
      <ProductDetail
        productId={selectedId}
        onBack={() => setSelected(null)}
      />
    )
  }

  const showHint    = !loading && results === null && !error
  const showEmpty   = !loading && results !== null && results.length === 0 && !error
  const showResults = !loading && results && results.length > 0

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* ── Search bar ── */}
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 16px', borderRadius: 14,
          border: '1.5px solid var(--border)',
          background: 'var(--surface)',
          boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
        }}
      >
        <span style={{ color: 'var(--text-3)', flexShrink: 0 }}><SearchIcon /></span>
        <input
          ref={inputRef}
          value={query}
          onChange={e => handleInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { clearTimeout(debounceRef.current); runSearch(query) } }}
          placeholder="ابحث عن منتج… مثلاً: زيت زيتون، غسالة، شامبو"
          dir="auto"
          style={{
            flex: 1, border: 'none', outline: 'none',
            background: 'transparent', fontSize: '0.95rem',
            color: 'var(--text-1)', fontFamily: 'inherit',
          }}
        />
        {loading && (
          <span style={{ color: 'var(--text-3)', fontSize: '0.75rem', flexShrink: 0 }}>
            جارٍ البحث…
          </span>
        )}
        {query && !loading && (
          <button
            onClick={handleClear}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-3)', padding: 2, display: 'flex', alignItems: 'center', flexShrink: 0,
            }}
            title="مسح"
          >
            <ClearIcon />
          </button>
        )}
      </div>

      {/* ── Result count ── */}
      {showResults && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-3)' }}>
          {results.length.toLocaleString('ar-SA')} نتيجة لـ "{query}"
        </div>
      )}

      {/* ── Error ── */}
      {error && (
        <div style={{
          padding: '10px 14px', borderRadius: 10,
          background: 'var(--rejected-bg)', border: '1px solid var(--border)',
          color: 'var(--rejected-fg)', fontSize: '0.82rem',
        }}>
          ⚠ {error}
        </div>
      )}

      {showHint  && <HintState />}
      {showEmpty && <EmptyState query={query} />}

      {showResults && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {results.map(r => (
            <ResultCard
              key={r.product_id}
              result={r}
              onClick={() => setSelected(r.product_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
