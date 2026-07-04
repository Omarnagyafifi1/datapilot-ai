import React from 'react';
import { COPY } from '../../lib/copy';

export default function SQLViewer({ sql, onChange, onRun, onRequestApproval, loading, requiresApproval }) {
  return (
    <div className="glass p-4 rounded-2xl border-white/5">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[12px] font-bold text-white/40 uppercase">{COPY.SQL_PREVIEW_TITLE}</div>
        <div className="text-[12px] text-muted">Editable - {COPY.PLEASE_REVIEW_SQL.toLowerCase()}</div>
      </div>

      <textarea
        value={sql}
        onChange={(e) => onChange(e.target.value)}
        className="w-full min-h-[140px] bg-black/40 font-mono text-xs text-blue-300 p-4 rounded resize-vertical"
      />

      <div className="mt-3 flex items-center gap-3">
        {requiresApproval ? (
          <button
            onClick={onRequestApproval}
            disabled={loading || !sql.trim()}
            className="py-2.5 px-6 bg-amber-500 text-black font-mono font-bold text-xs uppercase rounded-lg hover:bg-amber-400 disabled:opacity-40 transition-all shadow-lg shadow-amber-500/20 flex items-center gap-2"
          >
            {loading ? COPY.LOADING_RUNNING : (
              <><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>{COPY.APPROVE_EXECUTE}</>
            )}
          </button>
        ) : (
          <button
            onClick={onRun}
            disabled={loading || !sql.trim()}
            className="py-2.5 px-6 bg-cyber-cyan text-background font-mono font-bold text-xs uppercase rounded-lg hover:brightness-105 disabled:opacity-40 transition-all flex items-center gap-2"
          >
            {loading ? COPY.LOADING_RUNNING : (
              <><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 12h14M12 5l7 7-7 7" /></svg>{COPY.RUN_QUERY}</>
            )}
          </button>
        )}
        <div className="text-sm text-muted">{COPY.PLEASE_REVIEW_SQL}</div>
      </div>
    </div>
  );
}
