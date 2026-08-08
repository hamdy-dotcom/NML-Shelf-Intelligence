import { useEffect, useRef, useState } from 'react'
import { atlasApi, oracleApi } from '../../api/ledger.js'
import { ConfidenceBar } from '../../components/ConfidenceBar.jsx'
import { toast } from '../../components/Toast.jsx'

/* ─────────────────────────────────────────────────────────────
   Mock data — shown when API is unreachable
   ───────────────────────────────────────────────────────────── */
const MOCK_STORES = [
  { id: 'mock-store-1', name_ar: 'بندة — بانوراما مول، الرياض', name_en: 'Panda — Panorama Mall', city_ar: 'الرياض', cluster: { label: 'Riyadh — Premium', income_tier: 'high', footfall_tier: 'mid' } },
  { id: 'mock-store-2', name_ar: 'بندة — الأندلس، جدة',         name_en: 'Panda — Al-Andalus',    city_ar: 'جدة',     cluster: { label: 'Western Region — Premium', income_tier: 'high', footfall_tier: 'mid' } },
  { id: 'mock-store-3', name_ar: 'العثيم — مول العثيم، الرياض', name_en: 'Othaim — Othaim Mall',  city_ar: 'الرياض',  cluster: { label: 'Riyadh — Mass Market', income_tier: 'mid', footfall_tier: 'high' } },
  { id: 'mock-store-4', name_ar: 'العثيم — الدمام',              name_en: 'Othaim — Dammam',       city_ar: 'الدمام',  cluster: { label: 'Eastern Province — Oil Belt', income_tier: 'high', footfall_tier: 'mid' } },
]

const MOCK_RESULT = {
  recommendation_id: 'mock-rec-1',
  cluster_label: 'Riyadh — Premium',
  income_tier: 'high',
  footfall_tier: 'mid',
  category_filter: 'زيوت ودهون',
  category_filter_matched: false,
  candidates_evaluated: 12,
  top_k_returned: 3,
  reasoning_text: 'تم تقييم ١٢ منتجاً محلولاً. أعلى مرشح هو "زيت زيتون بكر ممتاز" بدرجة مركّبة ٧٦٪ — يتميز بحضور قوي في القوائم (سرعة=١.٠، إعلان=١.٠) ومستوى سعري مناسب لمجموعة الدخل المرتفع (+٦٪ فوق المتوسط). يُقدَّر فجوة الفئة بـ ٠.٥ (مؤقت — لا تتوفر بيانات التخزين الفعلي).',
  data_quality_notes: ['category_gap دائماً ٠.٥ — لا تتوفر بيانات التخزين الفعلي في المتاجر بعد'],
  ranked: [
    {
      rank: 1,
      product_id: 'bbbbbbbb-0001-0000-0000-000000000000',
      canonical_name_ar: 'زيت زيتون بكر ممتاز',
      canonical_name_en: 'Extra Virgin Olive Oil',
      category: null,
      median_price: 46.25,
      currency: 'SAR',
      listing_count: 2,
      ad_count: 24,
      total_score: 0.755,
      components: {
        velocity:     { raw_value: 2,  normalized: 1.0, weight: 0.30, weighted: 0.300, note: null },
        ad_intensity: { raw_value: 24, normalized: 1.0, weight: 0.25, weighted: 0.250, note: null },
        category_gap: { raw_value: null, normalized: 0.5, weight: 0.25, weighted: 0.125, note: 'مؤقت — لا تتوفر بيانات التخزين' },
        price_fit:    { raw_value: 1,  normalized: 0.8, weight: 0.20, weighted: 0.160, note: null },
      },
      reasoning_fragment: 'قوائم=٢، إعلانات=٢٤، سعر وسيط=٤٦.٢٥ ر.س (متوسط)، تطابق سعري مع الدخل المرتفع: ٨٠٪',
    },
    {
      rank: 2,
      product_id: 'bbbbbbbb-0002-0000-0000-000000000000',
      canonical_name_ar: 'عصير برتقال طازج',
      canonical_name_en: 'Fresh Orange Juice',
      category: null,
      median_price: 12.0,
      currency: 'SAR',
      listing_count: 1,
      ad_count: 8,
      total_score: 0.512,
      components: {
        velocity:     { raw_value: 1, normalized: 0.5, weight: 0.30, weighted: 0.150, note: null },
        ad_intensity: { raw_value: 8, normalized: 0.4, weight: 0.25, weighted: 0.100, note: null },
        category_gap: { raw_value: null, normalized: 0.5, weight: 0.25, weighted: 0.125, note: 'مؤقت' },
        price_fit:    { raw_value: 1, normalized: 0.7, weight: 0.20, weighted: 0.140, note: null },
      },
      reasoning_fragment: 'قوائم=١، إعلانات=٨، سعر وسيط=١٢.٠٠ ر.س، تطابق سعري: ٧٠٪',
    },
    {
      rank: 3,
      product_id: 'bbbbbbbb-0003-0000-0000-000000000000',
      canonical_name_ar: 'زيت نباتي متعدد الاستخدامات',
      canonical_name_en: 'Multi-Purpose Vegetable Oil',
      category: null,
      median_price: 22.5,
      currency: 'SAR',
      listing_count: 1,
      ad_count: 3,
      total_score: 0.388,
      components: {
        velocity:     { raw_value: 1, normalized: 0.5, weight: 0.30, weighted: 0.150, note: null },
        ad_intensity: { raw_value: 3, normalized: 0.1, weight: 0.25, weighted: 0.025, note: null },
        category_gap: { raw_value: null, normalized: 0.5, weight: 0.25, weighted: 0.125, note: 'مؤقت' },
        price_fit:    { raw_value: 1, normalized: 0.44, weight: 0.20, weighted: 0.088, note: null },
      },
      reasoning_fragment: 'قوائم=١، إعلانات=٣، سعر وسيط=٢٢.٥٠ ر.س، تطابق سعري: ٤٤٪',
    },
  ],
}

/* ─────────────────────────────────────────────────────────────
   Known categories — the oracle scorer is flexible (any string),
   but offer the most common for quick selection
   ───────────────────────────────────────────────────────────── */
const CATEGORIES = [
  { value: 'food',       label: 'مواد غذائية' },
  { value: 'household',  label: 'منزلية' },
  { value: 'personal',   label: 'عناية شخصية' },
  { value: 'beverages',  label: 'مشروبات' },
  { value: 'cleaning',   label: 'منظفات' },
  { value: 'baby',       label: 'أطفال' },
  { value: 'other',      label: 'أخرى' },
]

/* ─────────────────────────────────────────────────────────────
   Signal labels
   ───────────────────────────────────────────────────────────── */
const SIGNAL_LABELS = {
  velocity:     { label: 'السرعة',       desc: 'عدد القوائم المحلولة' },
  ad_intensity: { label: 'الإعلانات',    desc: 'إعلانات نشطة' },
  category_gap: { label: 'فجوة الفئة',   desc: 'تمثيل الفئة في المجموعة' },
  price_fit:    { label: 'ملاءمة السعر', desc: 'توافق مع مستوى الدخل' },
}

/* ─────────────────────────────────────────────────────────────
   Rank badge
   ───────────────────────────────────────────────────────────── */
function RankBadge({ rank }) {
  const colors = {
    1: { bg: 'var(--accent)', fg: '#fff' },
    2: { bg: '#9ca3af',       fg: '#fff' },
    3: { bg: '#d1d5db',       fg: 'var(--text-1)' },
  }
  const c = colors[rank] ?? { bg: 'var(--border)', fg: 'var(--text-2)' }
  return (
    <div style={{
      width: 28, height: 28, borderRadius: 999,
      background: c.bg, color: c.fg,
      fontWeight: 800, fontSize: '0.8rem',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
    }}>
      {rank}
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────
   Inline signal score bar (compact, 4-in-a-row)
   ───────────────────────────────────────────────────────────── */
function SignalMini({ signalKey, component }) {
  const meta  = SIGNAL_LABELS[signalKey] ?? { label: signalKey, desc: '' }
  const pct   = Math.round(component.normalized * 100)
  const isPlaceholder = component.note != null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3, flex: 1, minWidth: 60 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.62rem', color: 'var(--text-3)' }}>
        <span>{meta.label}</span>
        <span style={{ color: isPlaceholder ? 'var(--pending-fg)' : 'var(--text-2)', fontWeight: 600 }}>
          {pct}٪{isPlaceholder ? '*' : ''}
        </span>
      </div>
      <div style={{ height: 4, borderRadius: 999, background: 'var(--border)', overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          borderRadius: 999,
          background: isPlaceholder ? '#d97706' : 'var(--accent)',
          transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────
   Candidate card
   ───────────────────────────────────────────────────────────── */
function CandidateCard({ candidate, recId, reviewer, isOffline, picked, onPick, pickLoading }) {
  const [expanded, setExpanded] = useState(false)
  const isPicked   = picked === candidate.product_id
  const isDisabled = picked !== null || pickLoading

  const priceLabel = candidate.median_price != null
    ? `${candidate.median_price.toFixed(2)} ر.س`
    : null

  return (
    <div
      className="card"
      style={{
        display: 'flex', flexDirection: 'column', gap: 14,
        borderColor: isPicked ? 'var(--accent)' : '',
        boxShadow: isPicked ? '0 0 0 2px var(--accent)' : '',
        transition: 'border-color 0.2s, box-shadow 0.2s',
      }}
    >
      {/* Row 1: rank + name + pick button */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <RankBadge rank={candidate.rank} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text-1)', lineHeight: 1.4 }}>
            {candidate.canonical_name_ar ?? candidate.canonical_name_en ?? '—'}
          </div>
          {candidate.canonical_name_en && candidate.canonical_name_ar && (
            <div style={{ fontSize: '0.72rem', color: 'var(--text-3)', direction: 'ltr', textAlign: 'right', marginTop: 2 }}>
              {candidate.canonical_name_en}
            </div>
          )}
        </div>
        {isPicked ? (
          <span style={{
            padding: '5px 12px', borderRadius: 999,
            background: 'var(--approved-bg)', color: 'var(--approved-fg)',
            fontSize: '0.75rem', fontWeight: 700, flexShrink: 0,
          }}>
            ✓ تم الاختيار
          </span>
        ) : (
          <button
            className="btn-primary"
            style={{ flexShrink: 0, padding: '6px 14px', fontSize: '0.78rem' }}
            disabled={isDisabled}
            onClick={() => onPick(candidate.product_id, candidate.rank)}
          >
            {pickLoading && picked === null ? '...' : 'اختر هذا'}
          </button>
        )}
      </div>

      {/* Row 2: meta chips */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {candidate.listing_count != null && (
          <span className="label">🏷️ {candidate.listing_count.toLocaleString('ar-SA')} قائمة</span>
        )}
        {candidate.ad_count != null && (
          <span className="label">📣 {candidate.ad_count.toLocaleString('ar-SA')} إعلان</span>
        )}
        {priceLabel && (
          <span className="label">💰 {priceLabel}</span>
        )}
        {candidate.category && (
          <span className="label">🏷 {candidate.category}</span>
        )}
      </div>

      {/* Row 3: overall confidence */}
      <ConfidenceBar value={candidate.total_score} label="الدرجة الكلية" max={1} />

      {/* Row 4: signal breakdown */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {Object.entries(candidate.components).map(([k, v]) => (
          <SignalMini key={k} signalKey={k} component={v} />
        ))}
      </div>

      {/* Row 5: reasoning fragment (collapsible) */}
      {candidate.reasoning_fragment && (
        <div>
          <button
            onClick={() => setExpanded(v => !v)}
            style={{
              background: 'none', border: 'none', padding: 0, cursor: 'pointer',
              color: 'var(--text-3)', fontSize: '0.72rem', fontFamily: 'inherit',
              display: 'flex', alignItems: 'center', gap: 4,
            }}
          >
            <span style={{ display: 'inline-block', transform: expanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }}>▶</span>
            {expanded ? 'إخفاء التفاصيل' : 'تفاصيل التقييم'}
          </button>
          {expanded && (
            <p style={{
              margin: '6px 0 0', padding: '8px 12px', borderRadius: 8,
              background: 'var(--surface-2)', border: '1px solid var(--border-faint)',
              fontSize: '0.78rem', color: 'var(--text-2)', lineHeight: 1.7, direction: 'rtl',
            }}>
              {candidate.reasoning_fragment}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────
   Results panel (phase 3)
   ───────────────────────────────────────────────────────────── */
function ResultsPanel({ result, reviewer, isOffline, onReset }) {
  const [picked, setPicked]           = useState(null)
  const [pickLoading, setPickLoading] = useState(false)

  async function handlePick(productId, rank) {
    setPickLoading(true)
    try {
      if (isOffline) {
        await new Promise(r => setTimeout(r, 700))
        setPicked(productId)
        toast('تم تسجيل الاختيار (بيانات تجريبية)', 'info')
        return
      }
      if (rank === 1) {
        await oracleApi.approveRec(result.recommendation_id, reviewer)
      } else {
        await oracleApi.editRec(result.recommendation_id, reviewer, productId)
      }
      setPicked(productId)
      toast('تم تسجيل الاختيار في السجل', 'success')
    } catch (err) {
      toast(err.message ?? 'حدث خطأ', 'error')
    } finally {
      setPickLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Summary bar */}
      <div
        className="card-sm"
        style={{
          display: 'flex', flexWrap: 'wrap', gap: 12,
          alignItems: 'center', justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {result.cluster_label && (
            <span className="label">📍 {result.cluster_label}</span>
          )}
          {result.income_tier && (
            <span className="label">💳 دخل: {result.income_tier}</span>
          )}
          {result.category_filter && (
            <span className="label">🏷 {result.category_filter}</span>
          )}
          <span className="label">
            🏆 {(result.candidates_evaluated ?? 0).toLocaleString('ar-SA')} مرشح
          </span>
        </div>
        <button
          className="btn-ghost"
          style={{ fontSize: '0.75rem' }}
          onClick={onReset}
        >
          ← بحث جديد
        </button>
      </div>

      {/* Data quality notes */}
      {result.data_quality_notes?.length > 0 && (
        <div style={{
          padding: '8px 14px', borderRadius: 10,
          background: 'var(--pending-bg)', border: '1px solid var(--border)',
          fontSize: '0.75rem', color: 'var(--pending-fg)',
          display: 'flex', flexDirection: 'column', gap: 4,
        }}>
          {result.data_quality_notes.map((n, i) => (
            <div key={i} style={{ display: 'flex', gap: 6 }}>
              <span>⚠</span>
              <span>{n}</span>
            </div>
          ))}
        </div>
      )}

      {/* Reasoning summary */}
      {result.reasoning_text && (
        <div style={{
          padding: '12px 16px', borderRadius: 12,
          background: 'var(--surface-2)', border: '1px solid var(--border-faint)',
          fontSize: '0.82rem', color: 'var(--text-2)', lineHeight: 1.75,
        }}>
          {result.reasoning_text}
        </div>
      )}

      {/* Section heading */}
      <div style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.06em', color: 'var(--text-3)', textTransform: 'uppercase' }}>
        المرشحون ({(result.top_k_returned ?? result.ranked?.length ?? 0).toLocaleString('ar-SA')})
      </div>

      {/* Candidate cards */}
      {result.ranked?.map(c => (
        <CandidateCard
          key={c.product_id}
          candidate={c}
          recId={result.recommendation_id}
          reviewer={reviewer}
          isOffline={isOffline}
          picked={picked}
          onPick={handlePick}
          pickLoading={pickLoading}
        />
      ))}

      {result.ranked?.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: 32, color: 'var(--text-3)' }}>
          <div style={{ fontSize: 32 }}>🤷</div>
          <p style={{ margin: '8px 0 0', fontSize: '0.85rem' }}>
            لم يُعثر على مرشحين لهذه الفئة. جرّب فئة أخرى.
          </p>
        </div>
      )}
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────
   Main screen
   ───────────────────────────────────────────────────────────── */
export function OracleShelf({ reviewer }) {
  /* stores */
  const [stores, setStores]       = useState([])
  const [storesLoading, setStoresLoading] = useState(true)
  const [offline, setOffline]     = useState(false)

  /* form */
  const [storeId, setStoreId]     = useState('')
  const [category, setCategory]   = useState('food')
  const [customCat, setCustomCat] = useState('')
  const [openDate, setOpenDate]   = useState(new Date().toISOString().slice(0, 10))
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)

  /* results */
  const [result, setResult]       = useState(null)  // RecommendResponse

  /* Load stores on mount */
  useEffect(() => {
    atlasApi.stores()
      .then(data => {
        setStores(data.stores ?? [])
        setStoresLoading(false)
      })
      .catch(() => {
        setStores(MOCK_STORES)
        setOffline(true)
        setStoresLoading(false)
      })
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    const cat = category === 'other' ? customCat.trim() : category
    if (!cat) { setFormError('الرجاء إدخال اسم الفئة'); return }
    if (!storeId) { setFormError('الرجاء اختيار متجر'); return }

    setFormError(null)
    setSubmitting(true)
    try {
      if (offline) {
        await new Promise(r => setTimeout(r, 800))
        setResult({ ...MOCK_RESULT, category_filter: cat })
        return
      }

      // Step 1: create slot
      const slot = await oracleApi.createSlot({
        store_id: storeId,
        category: cat,
        open_date: new Date(openDate).toISOString(),
      })

      // Step 2: run scorer
      const rec = await oracleApi.recommend(slot.id)
      setResult(rec)
    } catch (err) {
      setFormError(err.message ?? 'تعذّر الاتصال بالخادم')
    } finally {
      setSubmitting(false)
    }
  }

  function handleReset() {
    setResult(null)
    setFormError(null)
  }

  /* ── If results are ready, show results panel ── */
  if (result) {
    return (
      <div style={{ maxWidth: 600, margin: '0 auto', padding: '24px 16px' }}>
        {offline && <OfflineBanner />}
        <ResultsPanel
          result={result}
          reviewer={reviewer}
          isOffline={offline}
          onReset={handleReset}
        />
      </div>
    )
  }

  const selectedStore = stores.find(s => s.id === storeId)

  /* ── Form phase ── */
  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: 24 }}>

      {offline && <OfflineBanner />}

      {/* Header */}
      <div>
        <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-1)' }}>
          توصية رف جديدة
        </h2>
        <p style={{ margin: '6px 0 0', fontSize: '0.82rem', color: 'var(--text-3)' }}>
          حدّد المتجر والفئة لتحليل أفضل المنتجات الملائمة لهذه الخانة
        </p>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Store picker */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-2)' }}>
            المتجر
          </label>
          {storesLoading ? (
            <div style={{ height: 44, borderRadius: 10, background: 'var(--border)', animation: 'pulse 1.4s infinite' }}>
              <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }`}</style>
            </div>
          ) : (
            <select
              required
              value={storeId}
              onChange={e => setStoreId(e.target.value)}
              style={{
                width: '100%', padding: '10px 14px', borderRadius: 10,
                border: '1.5px solid var(--border)',
                background: 'var(--surface)', color: 'var(--text-1)',
                fontSize: '0.9rem', fontFamily: 'inherit',
                appearance: 'none', outline: 'none', cursor: 'pointer',
              }}
            >
              <option value="">اختر متجراً…</option>
              {stores.map(s => (
                <option key={s.id} value={s.id}>
                  {s.name_ar}
                </option>
              ))}
            </select>
          )}
          {/* Store cluster info badge */}
          {selectedStore?.cluster && (
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <span className="label">📍 {selectedStore.cluster.label}</span>
              <span className="label">💳 دخل: {selectedStore.cluster.income_tier}</span>
              <span className="label">🚶 حركة: {selectedStore.cluster.footfall_tier}</span>
            </div>
          )}
        </div>

        {/* Category picker */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-2)' }}>
            الفئة
          </label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {CATEGORIES.map(c => (
              <button
                key={c.value}
                type="button"
                onClick={() => setCategory(c.value)}
                style={{
                  padding: '7px 16px', borderRadius: 999,
                  border: `1.5px solid ${category === c.value ? 'var(--accent)' : 'var(--border)'}`,
                  background: category === c.value ? 'var(--accent-bg)' : 'var(--surface)',
                  color: category === c.value ? 'var(--accent)' : 'var(--text-2)',
                  fontWeight: category === c.value ? 700 : 500,
                  fontSize: '0.82rem', fontFamily: 'inherit', cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {c.label}
              </button>
            ))}
          </div>
          {category === 'other' && (
            <input
              type="text"
              value={customCat}
              onChange={e => setCustomCat(e.target.value)}
              placeholder="اكتب اسم الفئة…"
              style={{
                padding: '10px 14px', borderRadius: 10,
                border: '1.5px solid var(--border)',
                background: 'var(--surface)', color: 'var(--text-1)',
                fontSize: '0.9rem', fontFamily: 'inherit', outline: 'none',
              }}
            />
          )}
        </div>

        {/* Open date */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-2)' }}>
            تاريخ الفتح
          </label>
          <input
            type="date"
            value={openDate}
            onChange={e => setOpenDate(e.target.value)}
            required
            style={{
              padding: '10px 14px', borderRadius: 10,
              border: '1.5px solid var(--border)',
              background: 'var(--surface)', color: 'var(--text-1)',
              fontSize: '0.9rem', fontFamily: 'inherit',
              outline: 'none', direction: 'ltr', textAlign: 'right',
            }}
          />
        </div>

        {/* Error */}
        {formError && (
          <div style={{
            padding: '10px 14px', borderRadius: 10,
            background: 'var(--rejected-bg)', color: 'var(--rejected-fg)', fontSize: '0.82rem',
          }}>
            ⚠ {formError}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          className="btn-primary"
          disabled={submitting || storesLoading}
          style={{ padding: '12px', fontSize: '0.95rem', fontWeight: 700 }}
        >
          {submitting ? 'جارٍ التحليل…' : '🔍 احسب التوصيات'}
        </button>
      </form>
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────
   Offline banner (reused from LedgerQueue pattern)
   ───────────────────────────────────────────────────────────── */
function OfflineBanner() {
  return (
    <div style={{
      padding: '10px 16px', borderRadius: 10,
      background: 'var(--pending-bg)', border: '1px solid var(--border)',
      fontSize: '0.8rem', color: 'var(--pending-fg)',
      display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4,
    }}>
      <span>⚠</span>
      الخادم غير متاح — عرض بيانات تجريبية.{' '}
      <code style={{ fontSize: '0.75rem', background: 'rgba(0,0,0,0.08)', padding: '1px 5px', borderRadius: 4 }}>
        docker compose up && uvicorn main:app
      </code>
    </div>
  )
}
