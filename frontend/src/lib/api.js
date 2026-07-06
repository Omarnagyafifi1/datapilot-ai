import axios from 'axios';

// When running in Vite dev server, requests to /api will be proxied to backend
// In production, the backend serves the frontend and handles /api directly
const API_BASE_URL = '/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  health: () => client.get('/health'),
  
  datasources: {
    list: () => client.get('/datasources'),
    connect: (data) => client.post('/datasources/connect', data),
    delete: (id) => client.delete(`/datasources/${id}`),
  },
  
  query: (question, sourceId, threadId, previewOnly = false, sql = null, config = {}, llmConfig = {}) => client.post('/query', {
    question,
    source_id: sourceId,
    thread_id: threadId,
    preview_only: previewOnly,
    sql: sql,
    // LLM config override
    provider: llmConfig.provider,
    model: llmConfig.model,
    temperature: llmConfig.temperature,
    max_tokens: llmConfig.maxTokens,
  }, config),
  queryApproval: (threadId, approved, config = {}) => client.post('/query/approval', { thread_id: threadId, approved }, config),
  queryPage: ({ sql, sourceId, page, pageSize }) => client.post('/query/page', {
    sql,
    source_id: sourceId,
    page,
    page_size: pageSize,
  }),
  explain: (sql) => client.post('/explain', { sql }),
  report: (document) => client.post('/report/generate', { document }),

  history: {
    list: () => client.get('/query-history'),
  },
  
  schema: {
    get: (sourceId) => client.get(`/datasources/${sourceId}/schema`),
    suggestions: (sourceId) => client.get(`/datasources/${sourceId}/suggestions`),
  },
  
  system: {
    stats: () => client.get('/system/stats'),
    feed: () => client.get('/system/feed'),
    metrics: () => client.get('/system/metrics'),
  },

  uploads: {
    uploadCsv: (formData) => client.post('/data/csv', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
    preview: (formData) => client.post('/upload/preview', formData, { 
      headers: { 'Content-Type': 'multipart/form-data' } 
    }),
    import: (formData) => client.post('/upload/import', formData, { 
      headers: { 'Content-Type': 'multipart/form-data' } 
    }),
  },
  
  datasets: {
    list: (search, sourceType) => client.get('/datasets', { 
      params: { search, source_type: sourceType } 
    }),
    get: (id) => client.get(`/datasets/${id}`),
    delete: (id) => client.delete(`/datasets/${id}`),
    update: (id, data) => client.patch(`/datasets/${id}`, data),
  },

  settings: {
    get: () => client.get('/settings/llm'),
    update: (data) => client.put('/settings/llm', data),
  },

  evaluate: (question, sql, sourceId) => client.post('/evaluate', {
    question,
    sql,
    source_id: sourceId,
  }),

  settings: {
    get: () => client.get('/settings'),
    update: (data) => client.post('/settings', data),
  },
};

export default api;