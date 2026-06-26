import React from 'react';
import { COPY } from '../lib/copy';

export function EmptyState({ title, examples = COPY.EMPTY_QUERY_EXAMPLES, onSelectExample }) {
  return (
    <div className="glass p-8 rounded-2xl border-dashed border-white/5 text-center animate-in fade-in zoom-in duration-300">
      <h4 className="text-lg font-bold mb-2">{title}</h4>
      <p className="text-sm text-muted mb-4">Try one of these example prompts:</p>
      <div className="flex justify-center gap-3 flex-wrap">
        {examples.map((e) => (
          <button 
            key={e} 
            onClick={() => onSelectExample && onSelectExample(e)}
            className="px-4 py-2 bg-white/[0.03] hover:bg-cyber-cyan/10 border border-white/5 hover:border-cyber-cyan/30 rounded font-mono text-[12px] text-cyber-cyan transition-all cursor-pointer hover:scale-105 active:scale-95"
          >
            {e}
          </button>
        ))}
      </div>
    </div>
  );
}

export default EmptyState;
