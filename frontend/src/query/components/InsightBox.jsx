import React from 'react';

export default function InsightBox({ insights = [], error = null }) {
  if (error) {
    return (
      <div className="glass p-4 rounded-2xl border-white/5 text-red-400">{error}</div>
    );
  }

  if (!insights || insights.length === 0) {
    return (
      <div className="glass p-4 rounded-2xl border-white/5 text-muted">No insights available.</div>
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
