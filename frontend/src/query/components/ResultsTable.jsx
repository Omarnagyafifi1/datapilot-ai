import React, { useState, useMemo } from 'react';

export default function ResultsTable({ data = [], loading }) {
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('asc');

  const columns = Object.keys(data[0] || {});

  const sorted = useMemo(() => {
    if (!sortCol) return data;
    const copy = [...data];
    copy.sort((a, b) => {
      const va = a[sortCol];
      const vb = b[sortCol];
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === 'number' && typeof vb === 'number') return sortDir === 'asc' ? va - vb : vb - va;
      const sa = String(va).toLowerCase();
      const sb = String(vb).toLowerCase();
      if (sa < sb) return sortDir === 'asc' ? -1 : 1;
      if (sa > sb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return copy;
  }, [data, sortCol, sortDir]);

  if (loading) {
    return (
      <div className="glass p-6 rounded-2xl border-white/5">
        <div className="animate-pulse text-muted">Loading results...</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="glass p-6 rounded-2xl border-white/5 text-muted">No results to display.</div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const slice = sorted.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="glass rounded-2xl border-white/5 overflow-hidden">
      <div className="p-3 flex items-center justify-between border-b border-white/5">
        <div className="text-[12px] text-white/60">{sorted.length} rows</div>
        <div className="text-[12px] text-white/40">Showing {slice.length} of {sorted.length}</div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className="bg-white/5">
              {columns.map((c) => (
                <th key={c} onClick={() => {
                  if (sortCol === c) setSortDir(sortDir === 'asc' ? 'desc' : 'asc'); else { setSortCol(c); setSortDir('asc'); }
                }} className="px-4 py-3 font-semibold text-white/60 border-b border-white/5 uppercase text-[10px] tracking-wider cursor-pointer">
                  <div className="flex items-center gap-2">
                    <span>{c}</span>
                    {sortCol === c && <span className="text-[10px]">{sortDir === 'asc' ? '▲' : '▼'}</span>}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {slice.map((row, i) => (
              <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                {columns.map((k, j) => (
                  <td key={j} className="px-4 py-3 text-white/80 whitespace-nowrap">{String(row[k] ?? '')}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="p-3 text-center bg-white/[0.02] border-t border-white/5 flex items-center justify-center gap-4">
        <button disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))} className="px-3 py-1 bg-white/5 rounded">Prev</button>
        <div className="text-[12px] text-white/40">Page {page} / {totalPages}</div>
        <button disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} className="px-3 py-1 bg-white/5 rounded">Next</button>
      </div>
    </div>
  );
}
