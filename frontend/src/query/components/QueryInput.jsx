import React from 'react';
import { COPY } from '../../lib/copy';

export default function QueryInput({ value, onChange, onPreview, loading, disabled }) {
  return (
    <div className="glass p-6 rounded-2xl border-white/5">
      <div className="flex items-start gap-4">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={disabled ? COPY.PLEASE_SELECT_SOURCE : 'Ask a question in plain English...'}
          className="w-full min-h-[96px] bg-transparent resize-none focus:outline-none text-white/90 font-mono p-4 rounded"
          disabled={disabled}
        />

        <div className="w-40 flex flex-col items-stretch gap-3">
          <button
            onClick={onPreview}
            disabled={loading || disabled || !value.trim()}
            className="py-3 px-4 bg-cyber-lime text-background font-mono font-bold text-xs uppercase rounded hover:brightness-110 disabled:opacity-40"
          >
            {loading ? COPY.LOADING_GENERATING : COPY.PREVIEW_SQL}
          </button>
          <p className="text-[12px] text-muted">Generate SQL from your natural language question. Review before executing.</p>
        </div>
      </div>
    </div>
  );
}
