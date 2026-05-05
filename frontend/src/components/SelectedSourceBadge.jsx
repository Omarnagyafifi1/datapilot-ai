import React from 'react';
import { COPY } from '../lib/copy';

export function SelectedSourceBadge({ source }) {
  if (!source) {
    return (
      <div className="px-3 py-1 bg-red-600/5 text-red-400 rounded-full text-[12px] font-mono font-bold">
        🔴 {COPY.SELECTED_NONE}
      </div>
    );
  }

  return (
    <div className="px-3 py-1 bg-green-600/5 text-cyber-cyan rounded-full text-[12px] font-mono font-bold flex items-center gap-2">
      <span className="text-cyber-lime">●</span>
      <span>{COPY.SELECTED_CONNECTED} {source.db_name || source.name}</span>
    </div>
  );
}

export default SelectedSourceBadge;
