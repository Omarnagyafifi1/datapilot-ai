import React from 'react';

export function Documentation() {
  return (
    <div className="p-12 max-w-5xl mx-auto">
      <h2 className="text-3xl font-extrabold mb-4">Documentation</h2>
      <p className="text-muted mb-6">Project documentation and API reference.</p>

      <div className="glass p-6 rounded-2xl border-white/5">
        <h3 className="text-xl font-bold mb-2">System Overview</h3>
        <p className="text-sm text-muted">The AI Text-to-SQL Data Analyst converts natural language into SQL, runs queries and returns visual and narrative insights.</p>
      </div>

      <div className="mt-6 glass p-6 rounded-2xl border-white/5">
        <h3 className="text-lg font-bold mb-2">API Endpoints (Draft)</h3>
        <ul className="list-disc pl-6 text-sm text-muted">
          <li><strong>POST /api/query</strong> — question &rarr; SQL &rarr; result</li>
          <li><strong>POST /api/datasources/connect</strong> — register external DB</li>
          <li><strong>GET /api/datasources/{id}/schema</strong> — schema</li>
          <li><strong>GET /api/query-history</strong> — query history</li>
        </ul>
      </div>
    </div>
  );
}

export default Documentation;
