import { useState } from 'react'

export function EditModal({ item, onSubmit, onClose, loading }) {
  const isGenome = item.type === 'genome_match'
  const isPrism  = item.type === 'prism_price'

  const [value, setValue] = useState(item.recommended_value ?? '')

  function handleSubmit(e) {
    e.preventDefault()
    if (!value.trim()) return
    onSubmit(value.trim())
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-1)' }}>
            تعديل التوصية
          </h3>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-3)', fontSize: 20, lineHeight: 1, padding: 4,
            }}
          >
            ×
          </button>
        </div>

        {/* Context */}
        <div
          style={{
            padding: '10px 14px',
            borderRadius: 10,
            background: 'var(--surface-2)',
            border: '1px solid var(--border)',
            marginBottom: 16,
            fontSize: '0.8rem',
            color: 'var(--text-2)',
          }}
        >
          {item.listing?.listing_title_raw ?? item.recommended_product?.canonical_name_ar ?? '—'}
        </div>

        <form onSubmit={handleSubmit}>
          <label style={{ display: 'block', marginBottom: 6, fontSize: '0.78rem', color: 'var(--text-2)', fontWeight: 600 }}>
            {isGenome
              ? 'معرّف المنتج الصحيح (UUID)'
              : isPrism
              ? 'السعر الموصى به (ر.س)'
              : 'القيمة المعدّلة'}
          </label>
          <input
            autoFocus
            value={value}
            onChange={e => setValue(e.target.value)}
            placeholder={isGenome ? 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' : ''}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 10,
              border: '1px solid var(--border)',
              background: 'var(--surface)',
              color: 'var(--text-1)',
              fontSize: '0.9rem',
              fontFamily: 'inherit',
              outline: 'none',
              textAlign: 'start',
              direction: isGenome ? 'ltr' : 'rtl',
            }}
          />

          <div style={{ display: 'flex', gap: 10, marginTop: 20, justifyContent: 'flex-end' }}>
            <button type="button" className="btn-ghost" onClick={onClose} disabled={loading}>
              إلغاء
            </button>
            <button type="submit" className="btn-primary" disabled={loading || !value.trim()}>
              {loading ? '...' : 'حفظ التعديل'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
