import { COPY } from '../lib/copy';

export function ConfirmationModal({ open, onClose, onConfirm, sql, source, requiresApproval }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-2xl bg-[#0b0b0b] border border-white/10 rounded-2xl p-6 shadow-2xl">
        <h3 className="text-lg font-bold mb-2 flex items-center gap-2">
          <span className="flex items-center gap-2">
            <svg className="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            {COPY.EXE_CONFIRM_TITLE}
          </span>
        </h3>
        
        {requiresApproval && (
          <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg text-xs leading-relaxed">
            <strong>Security Warning:</strong> This operation has been flagged as a data modification query (INSERT, UPDATE, or DELETE). Confirming this action will execute write modifications directly to the database.
          </div>
        )}

        <div className="text-sm text-muted mb-4">{source ? `${COPY.SELECTED_CONNECTED} ${source.db_name || source.name}` : COPY.SELECTED_NONE}</div>

        <div className="glass p-3 rounded mb-4 max-h-40 overflow-auto font-mono text-xs text-blue-200">{sql || <em className="text-muted">(No SQL)</em>}</div>

        <div className="flex items-center justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 bg-white/5 rounded transition hover:bg-white/10">{COPY.EXE_CONFIRM_CANCEL}</button>
          <button 
            onClick={onConfirm} 
            className={`px-5 py-2.5 rounded-lg font-bold transition-all flex items-center gap-2 shadow-lg ${requiresApproval ? 'bg-amber-500 text-black hover:bg-amber-400 shadow-amber-500/20' : 'bg-cyber-cyan text-background hover:opacity-90'}`}
          >
            {requiresApproval ? (
              <><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>{COPY.APPROVE_EXECUTE}</>
            ) : (
              <><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 12h14M12 5l7 7-7 7" /></svg>{COPY.EXE_CONFIRM_RUN}</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmationModal;
