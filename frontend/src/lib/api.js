import axios from 'axios';

// Use 127.0.0.1 to avoid localhost/IPv6 resolution issues in dev
const API_BASE_URL = 'http://127.0.0.1:8000/api';

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
  
  query: (question, sourceId) => client.post('/query', { question, source_id: sourceId }),
  explain: (sql) => client.post('/explain', { sql }),
  
  history: {
    list: () => client.get('/query-history'),
  },
  
  schema: {
    get: (sourceId) => client.get(`/datasources/${sourceId}/schema`),
  },
  
  system: {
    stats: () => client.get('/system/stats'),
    feed: () => client.get('/system/feed'),
  },

  uploads: {
    uploadCsv: (formData) => client.post('/data/csv', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  },
};

export default api;
