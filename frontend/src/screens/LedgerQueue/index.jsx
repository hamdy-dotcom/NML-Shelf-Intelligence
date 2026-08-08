import { useEffect, useRef, useState } from 'react'
import { ledgerApi } from '../../api/ledger.js'
import { QueueProgress } from '../../components/QueueProgress.jsx'
import { toast } from '../../components/Toast.jsx'
import { RecCard } from './RecCard.jsx'

/* ── Mock data (used when API is unreachable) ───────────────── */
const MOCK_ITEMS = [
  {
    id: 'mock-1',
    type: 'genome_match',
    status: 'pending',
    created_at: new Date().toISOString(),
    reasoning_text:
      'القائمة "زيت زيتون بكر ممتاز 750مل" من متجر النخيل تتطابق مع المنتج القانوني "زيت زيتون بكر ممتاز" بنسبة ثقة 92.4٪ باستخدام التطابق النصي المتجه.',
    recommended_value: 'aaaaaaaa-0001-0000-0000-000000000000',
    evidence_json: {
      listing_store: 'متجر النخيل',
      listing_title: 'زيت زيتون بكر ممتاز 750مل',
      listing_price_sar: '45.00',
      top_candidates: [
        { product_id: 'aaaaaaaa-0001-0000-0000-000000000000', similarity: 0.924, canonical_name_ar: 'زيت زيتون بكر ممتاز' },
        { product_id: 'aaaaaaaa-0002-0000-0000-000000000000', similarity: 0.781, canonical_name_ar: 'زيت نباتي متعدد الاستخدامات' },
      ],
    },
    listing: { store_name: 'متجر النخيل', listing_title_raw: 'زيت زيتون بكر ممتاز 750مل', price: 45.0, currency: 'SAR' },
    recommended_product: { canonical_name_ar: 'زيت زيتون بكر ممتاز', canonical_name_en: 'Extra Virgin Olive Oil' },
  },
  {
    id: 'mock-2',
    type: 'genome_match',
    status: 'pending',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    reasoning_text:
      'القائمة "عصير برتقال طازج 1 لتر" تتطابق مع "عصير برتقال طازج" بنسبة 88.1٪. النتيجة أقل من حد الثقة العالية (97٪) — يُوصى بمراجعة بشرية.',
    recommended_value: 'aaaaaaaa-0003-0000-0000-000000000000',
    evidence_json: {
      listing_store: 'بيت المنزل',
      listing_title: 'عصير برتقال طازج 1 لتر',
      listing_price_sar: '12.00',
      top_candidates: [
        { product_id: 'aaaaaaaa-0003-0000-0000-000000000000', similarity: 0.881, canonical_name_ar: 'عصير برتقال طازج' },
        { product_id: 'aaaaaaaa-0004-0000-0000-000000000000', similarity: 0.742, canonical_name_ar: 'عصير تفاح مصفى' },
      ],
    },
    listing: { store_name: 'بيت المنزل', listing_title_raw: 'عصير برتقال طازج 1 لتر', price: 12.0, currency: 'SAR' },
    recommended_product: { canonical_name_ar: 'عصير برتقال طازج', canonical_name_en: 'Fresh Orange Juice' },
  },
  {
    id: 'mock-3',
    type: 'prism_price',
    status: 'pending',
    created_at: new Date(Date.now() - 7200000).toISOString(),
    reasoning_text:
      'متوسط السعر عبر الإنترنت لـ 2 قائمة هو 46.25 ر.س. مجموعة "الرياض — المميزة" (income_tier=high, footfall_tier=mid): تعديل الطبقة +12٪، مضروباً في عامل مرونة الفئة الأساسية (0.5×)، يصل إلى تعديل نهائي +6٪. السعر الموصى به: 49.03 ر.س.',
    recommended_value: '49.03',
    evidence_json: {
      cluster_label: 'الرياض — المميزة',
      income_tier: 'high',
      footfall_tier: 'mid',
      cluster_adjustment: 0.06,
      recommended_price: '49.03',
      base_price: '46.25',
      listing_count: 2,
    },
    listing: null,
    recommended_product: { canonical_name_ar: 'زيت زيتون بكر ممتاز', canonical_name_en: 'Extra Virgin Olive Oil' },
  },
]

/* ── Loading skeleton ───────────────────────────────────────── */
function Skeleton() {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {[100, 140, 80, 60, 40].map((w, i) => (
        <div
          key={i}
          style={{
            height: 14,
            width: `${w}%`,
            borderRadius: 8,
            background: 'var(--border)',
            maxWidth: `${w}%`,
            animation: 'pulse 1.4s ease-in-out infinite',
          }}
        />
      ))}
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }`}</style>
    </div>
  )
}

/* ── Empty state ────────────────────────────────────────────── */
function EmptyState() {
  return (
    <div
      className="card"
      style={{ textAlign: 'center', padding: 48, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}
    >
      <span style={{ fontSize: 40 }}>✅</span>
      <p style={{ margin: 0, fontWeight: 700, fontSize: '1rem', color: 'var(--text-1)' }}>
        لا توجد توصيات معلقة
      </p>
      <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-3)' }}>
        سيظهر هنا أي تطابق جديد يحتاج مراجعة بشرية
      </p>
    </div>
  )
}

/* ── API offline banner ─────────────────────────────────────── */
function OfflineBanner() {
  return (
    <div
      style={{
        padding: '10px 16px',
        borderRadius: 10,
        background: 'var(--pending-bg)',
        border: '1px solid var(--border)',
        fontSize: '0.8rem',
        color: 'var(--pending-fg)',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        marginBottom: 16,
      }}
    >
      <span>⚠</span>
      الخادم غير متاح — عرض بيانات تجريبية. شغّل{' '}
      <code style={{ fontSize: '0.75rem', background: 'rgba(0,0,0,0.08)', padding: '1px 5px', borderRadius: 4 }}>
        docker compose up && uvicorn main:app
      </code>{' '}
      لعرض البيانات الحقيقية.
    </div>
  )
}

/* ── Main screen ────────────────────────────────────────────── */
export function LedgerQueue({ reviewer }) {
  const [items, setItems]               = useState([])
  const [loading, setLoading]           = useState(true)
  const [offline, setOffline]           = useState(false)
  const [cursor, setCursor]             = useState(0)   // index of currently visible card
  const [actionLoading, setActionLoading] = useState(null)  // 'approve' | 'reject' | 'edit'
  const didFetch = useRef(false)

  // Fetch queue
  useEffect(() => {
    if (didFetch.current) return
    didFetch.current = true

    ledgerApi.queue({ status: 'pending', limit: '50' })
      .then(data => {
        setItems(data.items ?? [])
        setLoading(false)
      })
      .catch(() => {
        setItems(MOCK_ITEMS)
        setOffline(true)
        setLoading(false)
      })
  }, [])

  async function handleAction(action, id, editedValue) {
    setActionLoading(action)
    try {
      if (offline) {
        // Simulate success on mock data
        await new Promise(r => setTimeout(r, 600))
        setItems(prev => prev.filter(it => it.id !== id))
        setCursor(c => Math.max(0, Math.min(c, items.length - 2)))
        toast(`تم ${action === 'approve' ? 'القبول' : action === 'reject' ? 'الرفض' : 'التعديل'} (بيانات تجريبية)`, 'info')
        return
      }

      if (action === 'approve') {
        await ledgerApi.approve(id, reviewer)
        toast('تم قبول التوصية', 'success')
      } else if (action === 'reject') {
        await ledgerApi.reject(id, reviewer)
        toast('تم رفض التوصية', 'success')
      } else if (action === 'edit') {
        await ledgerApi.edit(id, reviewer, editedValue)
        toast('تم حفظ التعديل', 'success')
      }

      // Remove reviewed item and advance cursor
      setItems(prev => prev.filter(it => it.id !== id))
      setCursor(c => Math.max(0, Math.min(c, items.length - 2)))
    } catch (err) {
      toast(err.message ?? 'حدث خطأ', 'error')
    } finally {
      setActionLoading(null)
    }
  }

  const total   = items.length
  const current = cursor + 1
  const item    = items[cursor]

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Offline warning */}
      {offline && <OfflineBanner />}

      {/* Progress */}
      {!loading && total > 0 && (
        <QueueProgress current={current} total={Math.min(total, 20)} />
      )}

      {/* Card area */}
      {loading ? (
        <Skeleton />
      ) : total === 0 ? (
        <EmptyState />
      ) : (
        <RecCard
          key={item.id}
          item={item}
          reviewer={reviewer}
          onAction={handleAction}
          actionLoading={actionLoading}
        />
      )}

      {/* Prev / Next navigation */}
      {!loading && total > 1 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            className="btn-ghost"
            disabled={cursor === 0 || actionLoading != null}
            onClick={() => setCursor(c => c - 1)}
          >
            {/* RTL: "Previous" = go right in list → left arrow visually becomes right */}
            ← السابق
          </button>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-3)' }}>
            {current.toLocaleString('ar-SA')} / {total.toLocaleString('ar-SA')}
          </span>
          <button
            className="btn-ghost"
            disabled={cursor >= total - 1 || actionLoading != null}
            onClick={() => setCursor(c => c + 1)}
          >
            التالي →
          </button>
        </div>
      )}
    </div>
  )
}
