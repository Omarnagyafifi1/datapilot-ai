import React from 'react';
import { Terminal, Lightbulb, Sparkles, Table as TableIcon, Calendar, CheckCircle2 } from 'lucide-react';
import { cn } from '../lib/utils';
import { api } from '../lib/api';

export function ResultVisualizer({ doc }) {
  if (!doc) return null;
  const [explainText, setExplainText] = React.useState(null);
  const [chartSvg, setChartSvg] = React.useState(null);
  const [showPreview, setShowPreview] = React.useState(false);

  return (
    <div className="mt-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard 
          icon={<TableIcon size={16} />} 
          label="Rows" 
          value={doc.results_count} 
          color="blue"
        />
        <MetricCard 
          icon={<Calendar size={16} />} 
          label="Executed" 
          value={new Date(doc.executed_at).toLocaleTimeString()} 
          color="purple"
        />
        <MetricCard 
          icon={<CheckCircle2 size={16} />} 
          label="Status" 
          value="Success" 
          color="green"
        />
      </div>

      {/* SQL Block */}
      <div className="glass rounded-2xl border-white/5 overflow-hidden">
        <div className="bg-white/5 px-4 py-2 flex items-center justify-between border-b border-white/5">
          <div className="flex items-center gap-2 text-[10px] font-bold text-white/40 uppercase tracking-widest">
            <Terminal size={12} /> Generated SQL
          </div>
        </div>
        <div className="p-4 bg-black/40 font-mono text-xs text-blue-300 leading-relaxed overflow-x-auto whitespace-pre">
          {doc.sql}
        </div>
        <div className="p-3 flex items-center gap-3 bg-white/2 border-t border-white/5">
          <button
            onClick={async () => {
              try {
                const resp = await api.explain(doc.sql);
                if (resp.data && resp.data.success) setExplainText(resp.data.data);
                else setExplainText('No explanation available.');
              } catch (e) {
                setExplainText('Explain request failed.');
              }
            }}
            className="px-3 py-1 text-xs font-mono bg-white/5 rounded hover:bg-white/10"
          >
            Explain Query
          </button>
          <button
            onClick={() => exportResultsCSV(doc.results, doc.suggestions)}
            className="px-3 py-1 text-xs font-mono bg-white/5 rounded hover:bg-white/10"
          >
            Export CSV
          </button>
          <button
            onClick={() => {
              const svg = buildChartSVG(doc.results);
              setChartSvg(svg);
              setShowPreview(true);
            }}
            className="px-3 py-1 text-xs font-mono bg-white/5 rounded hover:bg-white/10"
          >
            Preview Chart
          </button>
        </div>
      </div>

      {explainText && (
        <div className="mt-4 glass p-4 rounded-2xl border-white/5">
          <div className="text-[10px] font-bold text-white/40 uppercase mb-2">Query Explanation</div>
          <div className="text-sm text-white/80">{explainText}</div>
        </div>
      )}

      {showPreview && chartSvg && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowPreview(false)} />
          <div className="relative bg-card p-6 rounded-2xl w-[90%] max-w-3xl">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-lg font-bold">Chart Preview</h4>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => downloadSVG(chartSvg)}
                  className="px-3 py-1 text-xs font-mono bg-white/5 rounded"
                >Download SVG</button>
                <button
                  onClick={() => downloadPNGFromSVG(chartSvg)}
                  className="px-3 py-1 text-xs font-mono bg-white/5 rounded"
                >Download PNG</button>
                <button onClick={() => setShowPreview(false)} className="px-3 py-1 text-xs font-mono bg-white/5 rounded">Close</button>
              </div>
            </div>
            <div className="overflow-auto">
              <div dangerouslySetInnerHTML={{ __html: chartSvg }} />
            </div>
          </div>
        </div>
      )}

      {/* Results Table (Simplified for now) */}
      {doc.results && doc.results.length > 0 && (
        <div className="glass rounded-2xl border-white/5 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="bg-white/5">
                  {Object.keys(doc.results[0]).map(key => (
                    <th key={key} className="px-4 py-3 font-semibold text-white/60 border-b border-white/5 uppercase text-[10px] tracking-wider">
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {doc.results.slice(0, 5).map((row, i) => (
                  <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                    {Object.values(row).map((val, j) => (
                      <td key={j} className="px-4 py-3 text-white/80 whitespace-nowrap">
                        {String(val)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {doc.results_count > 5 && (
            <div className="p-3 text-center bg-white/[0.02] border-t border-white/5">
              <p className="text-[10px] text-white/40 uppercase font-bold">Showing 5 of {doc.results_count} results</p>
            </div>
          )}
        </div>
      )}

      {/* Insights and Suggestions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Insights */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-[10px] font-bold text-white/40 uppercase tracking-widest px-1">
            <Lightbulb size={12} className="text-amber-400" /> AI Insights
          </div>
          <div className="space-y-2">
            {doc.insights.map((insight, i) => (
              <div key={i} className="glass p-4 rounded-xl border-white/5 flex gap-3 group hover:border-white/10 transition-colors">
                <div className="w-1.5 h-1.5 rounded-full bg-primary mt-2 shrink-0 group-hover:scale-150 transition-transform" />
                <p className="text-sm text-white/80 leading-relaxed">
                  <span className="font-bold text-white">{insight.ar || insight.en}:</span> {insight.content || ""}
                  {/* Handle cases where insight might be just a string or object */}
                  {!insight.content && (insight.en || insight.ar || String(insight))}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Suggestions */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-[10px] font-bold text-white/40 uppercase tracking-widest px-1">
            <Sparkles size={12} className="text-purple-400" /> Next Steps
          </div>
          <div className="flex flex-col gap-2">
            {doc.suggestions.map((sug, i) => (
              <button 
                key={i} 
                className="text-left glass p-3 rounded-xl border-white/5 hover:bg-white/10 transition-all text-sm text-white/70 hover:text-white"
              >
                {sug.en || sug.ar || String(sug)}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, color }) {
  const colors = {
    blue: "text-blue-400 bg-blue-400/10",
    purple: "text-purple-400 bg-purple-400/10",
    green: "text-emerald-400 bg-emerald-400/10",
    amber: "text-amber-400 bg-amber-400/10",
  };
  
  return (
    <div className="glass p-4 rounded-2xl border-white/5">
      <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center mb-2", colors[color])}>
        {icon}
      </div>
      <p className="text-[10px] font-bold text-white/40 uppercase tracking-wider">{label}</p>
      <p className="text-lg font-bold text-white mt-1">{value}</p>
    </div>
  );
}

// Utilities: CSV export, chart (SVG) export, simple SQL explain
function exportResultsCSV(results = [], suggestions = []) {
  if (!results || results.length === 0) return;
  const keys = Object.keys(results[0]);
  const rows = [keys.join(',')];
  for (const r of results) {
    rows.push(keys.map(k => JSON.stringify(r[k] ?? '')).join(','));
  }
  const csv = rows.join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'results.csv';
  a.click();
  URL.revokeObjectURL(url);
}

function exportChartSVG(results = []) {
  // kept for backward compatibility; move to buildChartSVG for preview
  return buildChartSVG(results);
}

function escapeXml(unsafe) {
  return String(unsafe).replace(/[<>&'"']/g, function (c) {
    return {'<':'&lt;','>':'&gt;','&amp;':'&amp;','"':'&quot;','\'':'&#39;'}[c];
  });
}

function buildChartSVG(results = []) {
  if (!results || results.length === 0) return '';
  const first = results[0];
  const keys = Object.keys(first);
  let labelKey = keys.find(k => typeof first[k] === 'string') || keys[0];
  let valueKey = keys.find(k => typeof first[k] === 'number');
  if (!valueKey) valueKey = keys.find(k => !isNaN(Number(first[k])));
  if (!valueKey) return '';

  const labels = results.map(r => String(r[labelKey] ?? ''));
  const values = results.map(r => Number(r[valueKey] ?? 0));

  const width = Math.max(400, labels.length * 80);
  const height = 240;
  const maxVal = Math.max(...values, 1);
  const barW = Math.floor((width - 40) / values.length);

  let bars = '';
  values.forEach((v, i) => {
    const h = Math.round((v / maxVal) * (height - 80));
    const x = 20 + i * barW + 10;
    const y = height - 40 - h;
    bars += `<rect x="${x}" y="${y}" width="${barW - 12}" height="${h}" fill="#60A5FA"/>`;
    bars += `<text x="${x + (barW - 12) / 2}" y="${height - 20}" font-size="10" text-anchor="middle" fill="#E5E7EB">${escapeXml(labels[i])}</text>`;
  });

  const svg = `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">\n  <rect width="100%" height="100%" fill="#0b1220"/>\n  ${bars}\n</svg>`;
  return svg;
}

function downloadSVG(svg) {
  const blob = new Blob([svg], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'chart.svg';
  a.click();
  URL.revokeObjectURL(url);
}

function downloadPNGFromSVG(svg) {
  const img = new Image();
  const svgBlob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(svgBlob);
  img.onload = () => {
    const canvas = document.createElement('canvas');
    canvas.width = img.width;
    canvas.height = img.height;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#0b1220';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    canvas.toBlob((blob) => {
      const pngUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = pngUrl;
      a.download = 'chart.png';
      a.click();
      URL.revokeObjectURL(pngUrl);
      URL.revokeObjectURL(url);
    }, 'image/png');
  };
  img.onerror = () => {
    alert('Failed to convert SVG to PNG in this browser.');
    URL.revokeObjectURL(url);
  };
  img.src = url;
}
