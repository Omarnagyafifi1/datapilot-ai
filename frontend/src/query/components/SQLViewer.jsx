import React from 'react';
import { COPY } from '../../lib/copy';

export default function SQLViewer({ sql, onChange, onExecute, loading }) {
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
        <button
          onClick={onExecute}
          disabled={loading || !sql.trim()}
          className="py-2 px-4 bg-cyber-cyan text-background font-mono font-bold text-xs uppercase rounded hover:brightness-105 disabled:opacity-40"
        >
          {loading ? COPY.LOADING_RUNNING : COPY.RUN_QUERY}
        </button>
        <div className="text-sm text-muted">{COPY.PLEASE_REVIEW_SQL}</div>
      </div>
    </div>
  );
}
