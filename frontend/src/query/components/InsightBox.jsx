import React from 'react';

export default function InsightBox({ insights = [], error = null }) {
  if (error) {
    return (
      <div className="glass p-4 rounded-2xl border-white/5 text-red-400">{error}</div>
    );
  }

  if (!insights || insights.length === 0) {
    return (
      <div className="glass p-8 rounded-2xl border-white/5 flex flex-col items-center justify-center text-center">
        <div className="w-12 h-12 rounded-full bg-cyber-pink/10 flex items-center justify-center text-cyber-pink mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="M20 12h2"/><path d="m19.07 4.93-1.41 1.41"/><path d="M15.94 16c-.02.26-.06.51-.12.76"/><path d="M19.12 15.88c.19-.6.31-1.23.36-1.88"/><path d="M10.16 19.86A9.92 9.92 0 0 0 12 20c5.52 0 10-4.48 10-10 0-1.84-.5-3.56-1.35-5.02"/><path d="M14.6 20.73c-.64.13-1.3.2-1.98.2-5.52 0-10-4.48-10-10 0-.68.07-1.34.2-1.98"/><path d="m17.66 17.66-1.41-1.41"/><path d="m6.34 17.66 1.41-1.41"/><path d="M2 12h2"/><path d="M12 20v2"/></svg>
        </div>
        <h4 className="text-sm font-mono font-bold text-white uppercase tracking-widest mb-1">No Insights Generated</h4>
        <p className="text-xs text-muted max-w-sm leading-relaxed">Run a query to generate AI-powered insights and narratives from your data.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {insights.map((ins, i) => (
        <div key={i} className="glass p-4 rounded-xl border-white/5">
          <div className="text-sm text-white/80 leading-relaxed">{ins}</div>
        </div>
      ))}
    </div>
  );
}
