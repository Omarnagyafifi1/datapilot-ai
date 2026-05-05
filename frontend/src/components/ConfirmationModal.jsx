import React from 'react';
import { COPY } from '../lib/copy';

export function ConfirmationModal({ open, onClose, onConfirm, sql, source }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-2xl bg-[#0b0b0b] border border-white/10 rounded-2xl p-6">
        <h3 className="text-lg font-bold mb-2">{COPY.EXE_CONFIRM_TITLE}</h3>
        <div className="text-sm text-muted mb-4">{source ? `${COPY.SELECTED_CONNECTED} ${source.db_name || source.name}` : COPY.SELECTED_NONE}</div>

        <div className="glass p-3 rounded mb-4 max-h-40 overflow-auto font-mono text-xs text-blue-200">{sql || <em className="text-muted">(No SQL)</em>}</div>

        <div className="flex items-center justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 bg-white/5 rounded">{COPY.EXE_CONFIRM_CANCEL}</button>
          <button onClick={onConfirm} className="px-4 py-2 bg-cyber-cyan text-background rounded font-bold">{COPY.EXE_CONFIRM_RUN}</button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmationModal;
