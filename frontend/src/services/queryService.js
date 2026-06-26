import { api } from '../lib/api';
import { mock } from './mockData';

export const queryService = {
  generate: async (question, sourceId) => {
    try {
      const resp = await api.query(question, sourceId);
      if (resp && resp.data) {
        if (resp.data.success === false) {
          throw new Error(resp.data.message || 'Query failed on backend');
        }
        const d = resp.data.data || resp.data;
        return {
          sql: d.sql || d.generated_sql || resp.data.answer || '',
          results: d.results || d.rows || null,
          insights: d.insights || d.suggestions || d.explanation || [],
        };
      }
    } catch (e) {
      if (e.response?.data?.detail) throw new Error(e.response.data.detail);
      throw e;
    }
    return mock.generate(question);
  },

  execute: async (sql, sourceId) => {
    try {
      const resp = await api.query(sql, sourceId);
      if (resp && resp.data) {
        if (resp.data.success === false) {
          throw new Error(resp.data.message || 'Query execution failed');
        }
        const d = resp.data.data || resp.data;
        return {
          results: d.results || d.rows || [],
          insights: d.insights || d.suggestions || d.explanation || [],
        };
      }
    } catch (e) {
      if (e.response?.data?.detail) throw new Error(e.response.data.detail);
      throw e;
    }
    return mock.execute(sql);
  }
};

export default queryService;
