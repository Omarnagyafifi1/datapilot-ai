import React from 'react';
import { COPY } from '../lib/copy';

export function EmptyState({ title, examples = COPY.EMPTY_QUERY_EXAMPLES }) {
  return (
    <div className="glass p-8 rounded-2xl border-dashed border-white/5 text-center">
      <h4 className="text-lg font-bold mb-2">{title}</h4>
      <p className="text-sm text-muted mb-4">Try one of these example prompts:</p>
      <div className="flex justify-center gap-3 flex-wrap">
        {examples.map((e) => (
          <div key={e} className="px-3 py-2 bg-white/[0.02] rounded font-mono text-[12px] text-cyber-cyan">{e}</div>
        ))}
      </div>
    </div>
  );
}

export default EmptyState;
