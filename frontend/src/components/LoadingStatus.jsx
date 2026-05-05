import React from 'react';

export function LoadingStatus({ message }) {
  return (
    <div className="flex items-center gap-3 text-muted font-mono text-sm">
      <svg className="w-4 h-4 animate-spin text-cyber-cyan" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" /></svg>
      <div>{message}</div>
    </div>
  );
}

export default LoadingStatus;
