import { api } from '../lib/api';
import { mock } from './mockData';

export const queryService = {
  generate: async (question, sourceId) => {
    try {
      const resp = await api.query(question, sourceId);
      // Try to map likely shapes from backend
      if (resp && resp.data) {
        // backend may return { success, data: { sql, results, insights } }
        const d = resp.data.data || resp.data;
        return {
          sql: d.sql || d.generated_sql || resp.data.answer || '',
          results: d.results || d.rows || null,
          insights: d.insights || d.suggestions || d.explanation || [],
        };
      }
    } catch (e) {
      // fall through to mock
    }
    // fallback
    return mock.generate(question);
  },

  execute: async (sql, sourceId) => {
    try {
      // If backend supports an execute endpoint, use it; otherwise reuse query
      const resp = await api.query(sql, sourceId);
      if (resp && resp.data) {
        const d = resp.data.data || resp.data;
        return {
          results: d.results || d.rows || [],
          insights: d.insights || d.suggestions || d.explanation || [],
        };
      }
    } catch (e) {
      // fallback to mock
    }
    return mock.execute(sql);
  }
};

export default queryService;
