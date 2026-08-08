import { useEffect, useState } from 'react'
import { sentinelApi } from '../../api/ledger.js'
import { ConfidenceBar } from '../../components/ConfidenceBar.jsx'

/* ── Icons ─────────────────────────────────────────────────── */
function BackIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  )
}

function ExternalIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
      <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
    </svg>
  )
}

/* ── Resolved-by label ──────────────────────────────────────── */
const RESOLVED_LABELS = {
  'genome:text_embedding': 'تطابق نصي متجه',
  'genome:new_canonical':  'منتج جديد',
  'genome:manual':         'يدوي',
  'prism':                 'Prism',
}
function resolvedLabel(raw) {
  if (!raw) return null
  return RESOLVED_LABELS[raw] ?? raw
}

/* ── Price range bar ────────────────────────────────────────── */
function PriceRangeBar({ priceRange }) {
  if (!priceRange) return null
  const { min, max, median, currency = 'SAR' } = priceRange
  const spread = max - min || 1
  const medianPct = ((median - min) / spread) * 100

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-3)' }}>
        <span>أقل سعر: <strong style={{ color: 'var(--text-1)' }}>{min.toFixed(2)} {currency === 'SAR' ? 'ر.س' : currency}</strong></span>
        <span>أعلى سعر: <strong style={{ color: 'var(--text-1)' }}>{max.toFixed(2)} {currency === 'SAR' ? 'ر.س' : currency}</strong></span>
      </div>
      <div style={{ position: 'relative', height: 8, borderRadius: 999, background: 'var(--border)' }}>
        <div
          style={{
            position: 'absolute', inset: 0, borderRadius: 999,
            background: 'linear-gradient(90deg, var(--border) 0%, var(--accent) 100%)',
            opacity: 0.35,
          }}
        />
        {/* Median marker */}
        <div
          style={{
            position: 'absolute',
            left: `${medianPct}%`,
            top: -3, bottom: -3,
            width: 3, borderRadius: 999,
            background: 'var(--accent)',
            transform: 'translateX(-50%)',
          }}
          title={`الوسيط: ${median.toFixed(2)}`}
        />
      </div>
      <div style={{ textAlign: 'center', fontSize: '0.72rem', color: 'var(--text-3)' }}>
        الوسيط: <strong style={{ color: 'var(--accent)' }}>{median.toFixed(2)} {currency === 'SAR' ? 'ر.س' : currency}</strong>
      </div>
    </div>
  )
}

/* ── Store listing row ──────────────────────────────────────── */
function ListingRow({ listing }) {
  const { store_name, store_url, listing_title_raw, price, currency = 'SAR', scraped_at, resolved_by } = listing
  const label = resolvedLabel(resolved_by)

  return (
    <div
      style={{
        display: 'flex', flexDirection: 'column', gap: 6,
        padding: '12px 0',
        borderBottom: '1px solid var(--border-faint)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-1)' }}>
            {listing_title_raw}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 3 }}>
            {store_url ? (
              <a
                href={store_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  fontSize: '0.75rem', color: 'var(--text-3)',
                  textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 3,
                }}
              >
                {store_name}
                <ExternalIcon />
              </a>
            ) : (
              <span style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>{store_name}</span>
            )}
          </div>
        </div>
        <div style={{ textAlign: 'start', flexShrink: 0 }}>
          <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-1)' }}>
            {price?.toFixed(2)} {currency === 'SAR' ? 'ر.س' : currency}
          </div>
          {scraped_at && (
            <div style={{ fontSize: '0.65rem', color: 'var(--text-3)', marginTop: 2 }}>
              {new Date(scraped_at).toLocaleDateString('ar-SA', { month: 'short', day: 'numeric' })}
            </div>
          )}
        </div>
      </div>
      {label && (
        <span
          style={{
            alignSelf: 'flex-start',
            fontSize: '0.65rem', padding: '2px 7px', borderRadius: 999,
            background: 'var(--genome-bg)', color: 'var(--genome-fg)',
          }}
        >
          {label}
        </span>
      )}
    </div>
  )
}

/* ── Ad signals summary ─────────────────────────────────────── */
function AdSignalsSummary({ adSignals }) {
  if (!adSignals || adSignals.total_active == null) return null
  const platforms = adSignals.platforms ?? []

  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 16px', borderRadius: 10,
        background: 'var(--surface-2)', border: '1px solid var(--border)',
      }}
    >
      <div>
        <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--text-1)', lineHeight: 1 }}>
          {adSignals.total_active.toLocaleString('ar-SA')}
        </div>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-3)', marginTop: 2 }}>إعلان نشط</div>
      </div>
      {platforms.length > 0 && (
        <div style={{ display: 'flex', gap: 6 }}>
          {platforms.map(p => (
            <span
              key={p}
              style={{
                fontSize: '0.7rem', padding: '3px 9px', borderRadius: 999,
                background: 'var(--border)', color: 'var(--text-2)', fontWeight: 600,
              }}
            >
              {p === 'meta' ? 'Meta' : p === 'tiktok' ? 'TikTok' : p}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

/* ── Section heading ────────────────────────────────────────── */
function SectionHead({ title }) {
  return (
    <div style={{
      fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.06em',
      color: 'var(--text-3)', textTransform: 'uppercase', marginBottom: 4,
    }}>
      {title}
    </div>
  )
}

/* ── Skeleton loader ────────────────────────────────────────── */
function DetailSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '8px 0' }}>
      {[180, 120, 100, 80, 60, 140, 90].map((w, i) => (
        <div key={i} style={{
          height: 14, maxWidth: w, borderRadius: 8,
          background: 'var(--border)',
          animation: 'pulse 1.4s ease-in-out infinite',
        }} />
      ))}
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }`}</style>
    </div>
  )
}

/* ── Main detail panel (slide-over) ────────────────────────── */
export function ProductDetail({ productId, onBack }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    sentinelApi.product(productId)
      .then(d => { setData(d); setLoading(false) })
      .catch(err => { setError(err.message ?? 'حدث خطأ'); setLoading(false) })
  }, [productId])

  const product    = data?.product
  const listings   = data?.listings ?? []
  const priceRange = data?.price_range
  const adSignals  = data?.ad_signals

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 100,
        background: 'var(--bg)',
        overflowY: 'auto',
        animation: 'slideUp 0.22s ease-out',
      }}
    >
      <style>{`
        @keyframes slideUp {
          from { transform: translateY(24px); opacity: 0; }
          to   { transform: translateY(0);    opacity: 1; }
        }
      `}</style>

      {/* ── Sticky top bar ── */}
      <div
        style={{
          position: 'sticky', top: 0, zIndex: 10,
          background: 'var(--surface)',
          borderBottom: '1px solid var(--border)',
          padding: '0 16px',
          display: 'flex', alignItems: 'center', gap: 12, height: 52,
        }}
      >
        <button
          onClick={onBack}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-2)', padding: 6, display: 'flex', alignItems: 'center',
            borderRadius: 8, flexShrink: 0,
          }}
          title="رجوع"
        >
          <BackIcon />
        </button>
        <span style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-1)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {loading ? 'جارٍ التحميل…' : (product?.canonical_name_ar ?? product?.canonical_name_en ?? '—')}
        </span>
      </div>

      {/* ── Body ── */}
      <div style={{ maxWidth: 600, margin: '0 auto', padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {loading && <DetailSkeleton />}

        {error && (
          <div style={{
            padding: '12px 16px', borderRadius: 10,
            background: 'var(--rejected-bg)', color: 'var(--rejected-fg)', fontSize: '0.82rem',
          }}>
            ⚠ {error}
          </div>
        )}

        {!loading && !error && product && (
          <>
            {/* Product image + name */}
            {product.primary_image_url && (
              <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                <img
                  src={product.primary_image_url}
                  alt={product.canonical_name_ar ?? ''}
                  style={{
                    width: 72, height: 72, borderRadius: 12,
                    objectFit: 'cover', flexShrink: 0,
                    border: '1px solid var(--border)',
                  }}
                />
                <div>
                  <div style={{ fontWeight: 800, fontSize: '1.1rem', color: 'var(--text-1)', lineHeight: 1.4 }}>
                    {product.canonical_name_ar}
                  </div>
                  {product.canonical_name_en && (
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-3)', direction: 'ltr', marginTop: 3 }}>
                      {product.canonical_name_en}
                    </div>
                  )}
                  {product.category && (
                    <span className="label" style={{ marginTop: 6, display: 'inline-block' }}>
                      {product.category}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Price range */}
            {priceRange && (
              <div className="card-sm" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <SectionHead title="نطاق السعر" />
                <PriceRangeBar priceRange={priceRange} />
              </div>
            )}

            {/* Ad signals */}
            {adSignals && adSignals.total_active > 0 && (
              <div>
                <SectionHead title="إشارات الإعلان" />
                <AdSignalsSummary adSignals={adSignals} />
              </div>
            )}

            {/* Listings */}
            {listings.length > 0 && (
              <div>
                <SectionHead title={`القوائم (${listings.length.toLocaleString('ar-SA')})`} />
                <div className="card-sm" style={{ padding: '0 16px' }}>
                  {listings.map((l, i) => (
                    <ListingRow key={l.id ?? i} listing={l} />
                  ))}
                  {/* Remove bottom border on last row */}
                  <style>{`.card-sm > div:last-child { border-bottom: none !important; }`}</style>
                </div>
              </div>
            )}

            {/* GTIN if present */}
            {product.gtin && (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-3)' }}>
                GTIN: <span style={{ fontFamily: 'monospace' }}>{product.gtin}</span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
