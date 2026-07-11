import { api } from '../lib/api';
import { getErrorMessage } from '../lib/utils';

export const queryService = {
  generate: async (question, sourceId, llmConfig = {}) => {
    try {
      const resp = await api.query(question, sourceId, null, true, null, {}, llmConfig);
      if (resp && resp.data) {
        const data = resp.data.data ?? resp.data;
        if (data.success === false) {
          throw new Error(resp.data.message || 'Query failed on backend');
        }
        return {
          sql: data.sql || data.generated_sql || resp.data.answer || '',
          results: data.results || data.rows || null,
          insights: data.insights || [],
          suggestions: data.suggestions || [],
          requiresApproval: data.requires_approval || false,
          threadId: data.thread_id || null,
        };
      }
    } catch (e) {
      if (e.response?.data?.detail) throw new Error(getErrorMessage(e, 'Query failed on backend'), { cause: e });
      throw e;
    }
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
          insights: data.insights || [],
          suggestions: data.suggestions || [],
          requiresApproval: data.requires_approval || false,
          threadId: data.thread_id || null,
        };
      }
    } catch (e) {
      if (e.response?.data?.detail) throw new Error(getErrorMessage(e, 'Query execution failed'), { cause: e });
      throw e;
    }
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
          insights: data.insights || [],
          suggestions: data.suggestions || [],
          requiresApproval: data.requires_approval || false,
          threadId: data.thread_id || null,
          message: resp.data.message || '',
        };
      }
    } catch (e) {
      if (e.response?.data?.detail) throw new Error(getErrorMessage(e, 'Approval action failed'), { cause: e });
      throw e;
    }
    return { results: [], insights: [], suggestions: [], requiresApproval: false, threadId: null };
  }
};

export default queryService;
