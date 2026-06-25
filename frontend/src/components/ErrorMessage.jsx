import React from 'react';
import { AlertCircle } from 'lucide-react';
import { COPY } from '../lib/copy';

export function ErrorMessage({ title, reason }) {
  return (
    <div className="p-3 bg-red-600/10 border border-red-600/20 rounded flex items-start gap-3">
      <AlertCircle size={18} className="text-red-400" />
      <div>
        <div className="font-bold text-sm">{title || COPY.QUERY_FAILED_TITLE}</div>
        {reason && <div className="text-[12px] text-red-200 mt-1">Reason: {reason}</div>}
        <div className="text-[12px] text-muted mt-2">{COPY.QUERY_FAILED_TRY}</div>
      </div>
    </div>
  );
}

export default ErrorMessage;
