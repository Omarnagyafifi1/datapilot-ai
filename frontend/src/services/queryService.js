import { api } from '../lib/api';
import { mock } from './mockData';

export const queryService = {
  generate: async (question, sourceId) => {
    try {
      const resp = await api.query(question, sourceId, null, true);
      if (resp && resp.data) {
        const data = resp.data.data ?? resp.data;
        if (data.success === false) {
          throw new Error(resp.data.message || 'Query failed on backend');
        }
        return {
          sql: data.sql || data.generated_sql || resp.data.answer || '',
          results: data.results || data.rows || null,
          insights: data.insights || data.suggestions || data.explanation || [],
          requiresApproval: data.requires_approval || false,
          threadId: data.thread_id || null,
        };
      }
    } catch (e) {
      if (e.response?.data?.detail) throw new Error(e.response.data.detail, { cause: e });
      throw e;
    }
    return mock.generate(question);
  },

  execute: async (question, sql, sourceId, threadId) => {
    try {
      const resp = await api.query(question, sourceId, threadId, false, sql);
      if (resp && resp.data) {
        const data = resp.data.data ?? resp.data;
        if (data.success === false) {
          throw new Error(resp.data.message || 'Query execution failed');
        }
        return {
          results: data.results || data.rows || [],
          insights: data.insights || data.suggestions || data.explanation || [],
          requiresApproval: data.requires_approval || false,
          threadId: data.thread_id || null,
        };
      }
    } catch (e) {
      if (e.response?.data?.detail) throw new Error(e.response.data.detail, { cause: e });
      throw e;
    }
    return mock.execute(sql);
  },

  approve: async (threadId, approved) => {
    try {
      const resp = await api.queryApproval(threadId, approved);
      if (resp && resp.data) {
        const data = resp.data.data ?? resp.data;
        if (data.success === false) {
          throw new Error(resp.data.message || 'Approval action failed');
        }
        return {
          results: data.results || data.rows || [],
          insights: data.insights || data.suggestions || data.explanation || [],
          requiresApproval: data.requires_approval || false,
          threadId: data.thread_id || null,
          message: resp.data.message || '',
        };
      }
    } catch (e) {
      if (e.response?.data?.detail) throw new Error(e.response.data.detail, { cause: e });
      throw e;
    }
    return { results: [], insights: [], requiresApproval: false, threadId: null };
  }
};

export default queryService;
