import { api } from './client.js'

export const ledgerApi = {
  queue: (params = {}) => {
    const qs = new URLSearchParams({ status: 'pending', limit: '50', ...params })
    return api.get(`/ledger/queue?${qs}`)
  },
  approve: (id, reviewedBy) =>
    api.post(`/ledger/queue/${id}/approve`, { reviewed_by: reviewedBy }),
  reject:  (id, reviewedBy) =>
    api.post(`/ledger/queue/${id}/reject`,  { reviewed_by: reviewedBy }),
  edit:    (id, reviewedBy, editedValue) =>
    api.post(`/ledger/queue/${id}/edit`,   { reviewed_by: reviewedBy, edited_value: editedValue }),
}

export const sentinelApi = {
  search:  (q, limit = 8) => api.get(`/sentinel/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  product: (id)           => api.get(`/sentinel/product/${id}`),
}

export const atlasApi = {
  stores: () => api.get('/atlas/stores'),
}

export const oracleApi = {
  createSlot:  (body)    => api.post('/oracle/slots', body),
  recommend:   (slotId)  => api.post(`/oracle/slots/${slotId}/recommend`, {}),
  approveRec:  (recId, reviewer)              => api.post(`/ledger/queue/${recId}/approve`, { reviewed_by: reviewer }),
  editRec:     (recId, reviewer, productId)   => api.post(`/ledger/queue/${recId}/edit`,    { reviewed_by: reviewer, edited_value: productId }),
}
