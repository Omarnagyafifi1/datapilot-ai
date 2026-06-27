import { api } from '../lib/api';
import { mock } from './mockData';

export const queryService = {
  generate: async (question, sourceId) => {
    try {
      const resp = await api.query(question, sourceId, null, true);
      if (resp && resp.data) {
        if (resp.data.success === false) {
          throw new Error(resp.data.message || 'Query failed on backend');
        }
        const d = resp.data.data || resp.data;
        return {
          sql: d.sql || d.generated_sql || resp.data.answer || '',
          results: d.results || d.rows || null,
          insights: d.insights || d.suggestions || d.explanation || [],
          requiresApproval: d.requires_approval || false,
          threadId: d.thread_id || null,
        };
      }
    } catch (e) {
      if (e.response?.data?.detail) throw new Error(e.response.data.detail);
      throw e;
    }
    return mock.generate(question);
  },

  execute: async (question, sql, sourceId, threadId) => {
    try {
      const resp = await api.query(question, sourceId, threadId, false, sql);
      if (resp && resp.data) {
        if (resp.data.success === false) {
          throw new Error(resp.data.message || 'Query execution failed');
        }
        const d = resp.data.data || resp.data;
        return {
          results: d.results || d.rows || [],
          insights: d.insights || d.suggestions || d.explanation || [],
          requiresApproval: d.requires_approval || false,
          threadId: d.thread_id || null,
        };
      }
    } catch (e) {
      if (e.response?.data?.detail) throw new Error(e.response.data.detail);
      throw e;
    }
    return mock.execute(sql);
  },

  approve: async (threadId, approved) => {
    try {
      const resp = await api.queryApproval(threadId, approved);
      if (resp && resp.data) {
        if (resp.data.success === false) {
          throw new Error(resp.data.message || 'Approval action failed');
        }
        const d = resp.data.data || resp.data;
        return {
          results: d.results || d.rows || [],
          insights: d.insights || d.suggestions || d.explanation || [],
          requiresApproval: d.requires_approval || false,
          threadId: d.thread_id || null,
          message: resp.data.message || '',
        };
      }
    } catch (e) {
      if (e.response?.data?.detail) throw new Error(e.response.data.detail);
      throw e;
    }
    return { results: [], insights: [], requiresApproval: false, threadId: null };
  }
};

export default queryService;
