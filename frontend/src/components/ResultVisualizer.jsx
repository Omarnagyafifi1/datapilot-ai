import React from 'react';
import { Calendar, CheckCircle2, Download, FileText, Lightbulb, Sparkles, Table as TableIcon, Terminal } from 'lucide-react';
import { api } from '../lib/api';
import { cn } from '../lib/utils';

const PAGE_SIZE = 10;

export function ResultVisualizer({ doc }) {
  const [explainText, setExplainText] = React.useState(null);
  const [chartSvg, setChartSvg] = React.useState('');
  const [showPreview, setShowPreview] = React.useState(false);
  const [page, setPage] = React.useState(1);
  const [pageRows, setPageRows] = React.useState(null);
  const [pageLoading, setPageLoading] = React.useState(false);

  if (!doc) return null;

  const rows = pageRows || doc.results || [];
  const totalRows = doc.results_count || rows.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / PAGE_SIZE));
  const fallbackSlice = (doc.results || []).slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const visibleRows = pageRows || fallbackSlice;
  const visualization = doc.visualization || {};

  async function loadPage(nextPage) {
    setPage(nextPage);
    if (!doc.source_id || !doc.sql) return;
    setPageLoading(true);
    try {
      const resp = await api.queryPage({
        sql: doc.sql,
        sourceId: doc.source_id,
        page: nextPage,
        pageSize: PAGE_SIZE,
      });
      setPageRows(resp.data.data.rows || []);
    } catch {
      setPageRows(null);
    } finally {
      setPageLoading(false);
    }
  }

  return (
    <div className="mt-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={<TableIcon size={16} />} label="Rows" value={totalRows} color="blue" />
        <MetricCard icon={<Calendar size={16} />} label="Executed" value={formatTime(doc.executed_at)} color="purple" />
        <MetricCard icon={<CheckCircle2 size={16} />} label="Status" value="Success" color="green" />
        <MetricCard icon={<Sparkles size={16} />} label="Chart" value={visualization.chart_type || 'None'} color="amber" />
      </div>

      <div className="glass rounded-2xl border-white/5 overflow-hidden">
        <div className="bg-white/5 px-4 py-2 flex items-center justify-between border-b border-white/5">
          <div className="flex items-center gap-2 text-[10px] font-bold text-white/40 uppercase tracking-widest">
            <Terminal size={12} /> Generated SQL
          </div>
        </div>
        <div className="p-4 bg-black/40 font-mono text-xs text-blue-300 leading-relaxed overflow-x-auto whitespace-pre">
          {doc.sql}
        </div>
        <div className="p-3 flex flex-wrap items-center gap-3 bg-white/2 border-t border-white/5">
          <ActionButton onClick={async () => {
            try {
              const resp = await api.explain(doc.sql);
              setExplainText(resp.data?.success ? resp.data.data : 'No explanation available.');
            } catch {
              setExplainText('Explain request failed.');
            }
          }}>
            Explain
          </ActionButton>
          <ActionButton onClick={() => exportResultsCSV(doc.results || [])}>Export CSV</ActionButton>
          <ActionButton onClick={() => {
            const svg = buildChartSVG(doc.results || [], visualization.chart_type);
            setChartSvg(svg);
            setShowPreview(true);
          }}>
            Preview Chart
          </ActionButton>
          <ActionButton onClick={() => exportReport(doc)}>
            <FileText size={12} /> Export Report
          </ActionButton>
        </div>
      </div>

      {explainText && (
        <div className="glass p-4 rounded-2xl border-white/5">
          <div className="text-[10px] font-bold text-white/40 uppercase mb-2">Query Explanation</div>
          <div className="text-sm text-white/80">{explainText}</div>
        </div>
      )}

      {showPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowPreview(false)} />
          <div className="relative bg-card p-6 rounded-2xl w-[90%] max-w-3xl border border-white/10">
            <div className="flex items-center justify-between mb-4 gap-4">
              <h4 className="text-lg font-bold">Chart Preview</h4>
              <div className="flex items-center gap-2">
                <ActionButton onClick={() => downloadSVG(chartSvg)}>SVG</ActionButton>
                <ActionButton onClick={() => downloadPNGFromSVG(chartSvg)}>PNG</ActionButton>
                <ActionButton onClick={() => setShowPreview(false)}>Close</ActionButton>
              </div>
            </div>
            <div className="overflow-auto">{chartSvg ? <div dangerouslySetInnerHTML={{ __html: chartSvg }} /> : <p>No chart available.</p>}</div>
          </div>
        </div>
      )}

      {visibleRows.length > 0 && (
        <div className="glass rounded-2xl border-white/5 overflow-hidden">
          <div className="p-3 flex items-center justify-between border-b border-white/5">
            <div className="text-[12px] text-white/60">{totalRows} rows</div>
            <div className="text-[12px] text-white/40">{pageLoading ? 'Loading page...' : `Page ${page} / ${totalPages}`}</div>
          </div>
          <ResultsTable rows={visibleRows} />
          <div className="p-3 text-center bg-white/[0.02] border-t border-white/5 flex items-center justify-center gap-4">
            <ActionButton disabled={page <= 1 || pageLoading} onClick={() => loadPage(Math.max(1, page - 1))}>Prev</ActionButton>
            <ActionButton disabled={page >= totalPages || pageLoading} onClick={() => loadPage(Math.min(totalPages, page + 1))}>Next</ActionButton>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <InsightList title="AI Insights" icon={<Lightbulb size={12} className="text-amber-400" />} items={doc.insights || []} />
        <InsightList title="Next Steps" icon={<Sparkles size={12} className="text-purple-400" />} items={doc.suggestions || []} />
      </div>
    </div>
  );
}

function ResultsTable({ rows }) {
  const columns = Object.keys(rows[0] || {});
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm border-collapse">
        <thead>
          <tr className="bg-white/5">
            {columns.map((key) => (
              <th key={key} className="px-4 py-3 font-semibold text-white/60 border-b border-white/5 uppercase text-[10px] tracking-wider">
                {key}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-white/[0.02] transition-colors">
              {columns.map((key) => (
                <td key={key} className="px-4 py-3 text-white/80 whitespace-nowrap">{String(row[key] ?? '')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InsightList({ title, icon, items }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-[10px] font-bold text-white/40 uppercase tracking-widest px-1">
        {icon} {title}
      </div>
      <div className="space-y-2">
        {items.length === 0 ? (
          <div className="glass p-4 rounded-xl border-white/5 text-sm text-white/60">No items available.</div>
        ) : items.map((item, i) => {
          const isObj = typeof item === 'object' && item !== null;
          const enText = isObj ? (item.en || '') : String(item);
          const arText = isObj ? (item.ar || '') : '';
          return (
            <div key={i} className="glass p-4 rounded-xl border-white/5 flex flex-col gap-2 hover:border-white/10 transition-colors">
              {enText && <div className="text-sm text-white/80 leading-relaxed font-sans">{enText}</div>}
              {arText && <div className="text-sm text-cyber-cyan/95 leading-relaxed font-sans text-right" dir="rtl">{arText}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, color }) {
  const colors = {
    blue: 'text-blue-400 bg-blue-400/10',
    purple: 'text-purple-400 bg-purple-400/10',
    green: 'text-emerald-400 bg-emerald-400/10',
    amber: 'text-amber-400 bg-amber-400/10',
  };

  return (
    <div className="glass p-4 rounded-2xl border-white/5">
      <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center mb-2', colors[color])}>{icon}</div>
      <p className="text-[10px] font-bold text-white/40 uppercase tracking-wider">{label}</p>
      <p className="text-lg font-bold text-white mt-1">{value}</p>
    </div>
  );
}

function ActionButton({ children, disabled, onClick }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="inline-flex items-center gap-2 px-3 py-1 text-xs font-mono bg-white/5 rounded hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none"
    >
      {children}
    </button>
  );
}

function formatTime(value) {
  if (!value) return 'Now';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Now' : date.toLocaleTimeString();
}

function exportResultsCSV(results = []) {
  if (!results.length) return;
  const keys = Object.keys(results[0]);
  const rows = [keys.join(',')];
  for (const row of results) {
    rows.push(keys.map((key) => JSON.stringify(row[key] ?? '')).join(','));
  }
  downloadBlob(rows.join('\n'), 'results.csv', 'text/csv;charset=utf-8;');
}

async function exportReport(doc) {
  try {
    const resp = await api.report(doc);
    const report = resp.data.data;
    downloadBlob(report.markdown, report.filename || 'datapilot-report.md', 'text/markdown;charset=utf-8;');
  } catch {
    const fallback = `# ${doc.question || 'DataPilot Report'}\n\n## SQL\n\n\`\`\`sql\n${doc.sql || ''}\n\`\`\`\n`;
    downloadBlob(fallback, 'datapilot-report.md', 'text/markdown;charset=utf-8;');
  }
}

function downloadBlob(content, filename, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function escapeXml(value) {
  return String(value).replace(/[<>&"']/g, (char) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&#39;' }[char]));
}

function buildChartSVG(results = [], chartType = 'bar') {
  if (!results.length) return '';
  const keys = Object.keys(results[0]);
  const labelKey = keys.find((key) => typeof results[0][key] === 'string') || keys[0];
  const valueKey = keys.find((key) => Number.isFinite(Number(results[0][key])));
  if (!valueKey) return '';
  const labels = results.slice(0, 12).map((row) => String(row[labelKey] ?? ''));
  const values = results.slice(0, 12).map((row) => Number(row[valueKey] ?? 0));
  return chartType === 'pie' ? buildPieSVG(labels, values) : buildBarSVG(labels, values);
}

function buildBarSVG(labels, values) {
  const width = Math.max(420, labels.length * 86);
  const height = 260;
  const maxVal = Math.max(...values, 1);
  const barW = Math.floor((width - 48) / values.length);
  const bars = values.map((value, i) => {
    const h = Math.round((value / maxVal) * (height - 90));
    const x = 24 + i * barW + 8;
    const y = height - 44 - h;
    return `<rect x="${x}" y="${y}" width="${Math.max(12, barW - 16)}" height="${h}" fill="#60A5FA"/><text x="${x + (barW - 16) / 2}" y="${height - 20}" font-size="10" text-anchor="middle" fill="#E5E7EB">${escapeXml(labels[i])}</text>`;
  }).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><rect width="100%" height="100%" fill="#0b1220"/>${bars}</svg>`;
}

function buildPieSVG(labels, values) {
  const total = values.reduce((sum, value) => sum + Math.max(0, value), 0) || 1;
  let offset = 0;
  const colors = ['#60A5FA', '#A78BFA', '#34D399', '#F59E0B', '#F472B6', '#22D3EE'];
  const slices = values.map((value, i) => {
    const pct = Math.max(0, value) / total;
    const dash = `${pct * 100} ${100 - pct * 100}`;
    const slice = `<circle r="70" cx="120" cy="120" fill="transparent" stroke="${colors[i % colors.length]}" stroke-width="42" stroke-dasharray="${dash}" stroke-dashoffset="${-offset}" transform="rotate(-90 120 120)"/>`;
    offset += pct * 100;
    return slice;
  }).join('');
  const legend = labels.map((label, i) => `<text x="230" y="${54 + i * 22}" font-size="12" fill="#E5E7EB">${escapeXml(label)}</text>`).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="440" height="260"><rect width="100%" height="100%" fill="#0b1220"/>${slices}${legend}</svg>`;
}

function downloadSVG(svg) {
  if (!svg) return;
  downloadBlob(svg, 'chart.svg', 'image/svg+xml;charset=utf-8;');
}

function downloadPNGFromSVG(svg) {
  if (!svg) return;
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
      const anchor = document.createElement('a');
      anchor.href = pngUrl;
      anchor.download = 'chart.png';
      anchor.click();
      URL.revokeObjectURL(pngUrl);
      URL.revokeObjectURL(url);
    }, 'image/png');
  };
  img.onerror = () => URL.revokeObjectURL(url);
  img.src = url;
}
