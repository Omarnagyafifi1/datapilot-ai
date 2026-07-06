import React from 'react';
import { 
  Calendar, CheckCircle2, FileText, Lightbulb, Sparkles, Table as TableIcon, Terminal, BarChart3 
} from 'lucide-react';
import { api } from '../lib/api';
import { cn } from '../lib/utils';

const PAGE_SIZE = 10;

function loadPlotly(callback) {
  if (window.Plotly) { callback(window.Plotly); return; }
  const script = document.createElement('script');
  script.src = 'https://cdn.plot.ly/plotly-2.35.2.min.js';
  script.onload = () => callback(window.Plotly);
  document.head.appendChild(script);
}

export function ResultVisualizer({ doc }) {
  const [explainText, setExplainText] = React.useState(null);
  const [chartSvg, setChartSvg] = React.useState('');
  const [showPreview, setShowPreview] = React.useState(false);
  const [page, setPage] = React.useState(1);
  const [pageRows, setPageRows] = React.useState(null);
  const [pageLoading, setPageLoading] = React.useState(false);
  const chartRef = React.useRef(null);
  const [chartRendered, setChartRendered] = React.useState(false);

  if (!doc) return null;

  const rows = pageRows || doc.results || [];
  const totalRows = doc.results_count || rows.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / PAGE_SIZE));
  const fallbackSlice = (doc.results || []).slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const visibleRows = pageRows || fallbackSlice;
  const visualization = doc.visualization || {};
  const hasPlotlySpec = visualization && visualization.spec && visualization.spec.data;

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
      const payload = resp.data?.data ?? resp.data ?? {};
      setPageRows(payload.rows || []);
    } catch {
      setPageRows(null);
    } finally {
      setPageLoading(false);
    }
  }

  function openChartPreview() {
    setShowPreview(true);
    setChartRendered(false);
  }

  React.useEffect(() => {
    if (!showPreview || !hasPlotlySpec || chartRendered) return;
    loadPlotly((Plotly) => {
      if (chartRef.current && !chartRendered) {
        Plotly.newPlot(chartRef.current, visualization.spec.data, visualization.spec.layout || {}, {
          responsive: true,
          displayModeBar: true,
        });
        setChartRendered(true);
      }
    });
  }, [showPreview, hasPlotlySpec, chartRendered, visualization.spec]);

  React.useEffect(() => {
    if (!showPreview) {
      setChartRendered(false);
    }
  }, [showPreview]);

  return (
    <div className="mt-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={<TableIcon size={16} />} label="Rows" value={totalRows} color="blue" />
        <MetricCard icon={<Calendar size={16} />} label="Executed" value={formatTime(doc.executed_at)} color="purple" />
        <MetricCard icon={<CheckCircle2 size={16} />} label="Status" value="Success" color="green" />
        <MetricCard icon={<BarChart3 size={16} />} label="Chart" value={hasPlotlySpec ? visualization.chart_type || 'Available' : 'None'} color={hasPlotlySpec ? 'amber' : 'gray'} />
      </div>

      <div className="glass rounded-2xl border-border overflow-hidden">
        <div className="bg-foreground/5 px-4 py-2 flex items-center justify-between border-b border-border">
          <div className="flex items-center gap-2 text-[10px] font-bold text-foreground/40 uppercase tracking-widest">
            <Terminal size={12} /> Generated SQL
          </div>
        </div>
        <div className="p-4 bg-background/50 font-mono text-xs text-cyber-cyan/90 leading-relaxed overflow-x-auto whitespace-pre">
          {doc.sql}
        </div>
        <div className="p-3 flex flex-wrap items-center gap-3 bg-foreground/2 border-t border-border">
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
          {hasPlotlySpec && (
            <ActionButton onClick={openChartPreview}>
              <BarChart3 size={12} /> Plotly Chart
            </ActionButton>
          )}
          {!hasPlotlySpec && (
            <ActionButton onClick={() => {
              const svg = buildChartSVG(doc.results || [], visualization.chart_type || 'bar');
              setChartSvg(svg);
              setShowPreview(true);
            }}>
              Preview Chart
            </ActionButton>
          )}
          <ActionButton onClick={() => exportReport(doc)}>
            <FileText size={12} /> Export Report
          </ActionButton>
        </div>
      </div>

      {explainText && (
        <div className="glass p-4 rounded-2xl border-border">
          <div className="text-[10px] font-bold text-foreground/40 uppercase mb-2">Query Explanation</div>
          <div className="text-sm text-foreground/80">{explainText}</div>
        </div>
      )}

      {showPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowPreview(false)} />
          <div className="relative bg-card p-6 rounded-2xl w-[95%] max-w-5xl h-[85vh] border border-white/10 flex flex-col">
            <div className="flex items-center justify-between mb-4 gap-4 shrink-0">
              <h4 className="text-lg font-bold">
                {hasPlotlySpec ? `Chart Preview — ${visualization.chart_type}` : 'Simple Chart Preview'}
              </h4>
              <div className="flex items-center gap-2">
                {!hasPlotlySpec && <ActionButton onClick={() => downloadSVG(chartSvg)}>SVG</ActionButton>}
                {!hasPlotlySpec && <ActionButton onClick={() => downloadPNGFromSVG(chartSvg)}>PNG</ActionButton>}
                <ActionButton onClick={() => setShowPreview(false)}>Close</ActionButton>
              </div>
            </div>
            <div className="flex-1 overflow-auto min-h-0">
              {hasPlotlySpec ? (
                <div ref={chartRef} className="w-full h-full min-h-[400px]" />
              ) : chartSvg ? (
                <div dangerouslySetInnerHTML={{ __html: chartSvg }} />
              ) : (
                <p className="text-muted text-sm">No chart available.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {visibleRows.length > 0 && (
        <div className="glass rounded-2xl border-border overflow-hidden">
          <div className="p-3 flex items-center justify-between border-b border-border">
            <div className="text-[12px] text-foreground/60">{totalRows} rows</div>
            <div className="text-[12px] text-foreground/40">{pageLoading ? 'Loading page...' : `Page ${page} / ${totalPages}`}</div>
          </div>
          <ResultsTable rows={visibleRows} />
          <div className="p-3 text-center bg-foreground/[0.02] border-t border-border flex items-center justify-center gap-4">
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
          <tr className="bg-foreground/5">
            {columns.map((key) => (
              <th key={key} className="px-4 py-3 font-semibold text-foreground/60 border-b border-border uppercase text-[10px] tracking-wider">
                {key}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-foreground/[0.02] transition-colors">
              {columns.map((key) => (
                <td key={key} className="px-4 py-3 text-foreground/80 whitespace-nowrap">{String(row[key] ?? '')}</td>
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
      <div className="flex items-center gap-2 text-[10px] font-bold text-foreground/40 uppercase tracking-widest px-1">
        {icon} {title}
      </div>
      <div className="space-y-2">
        {items.length === 0 ? (
          <div className="glass p-4 rounded-xl border-border text-sm text-foreground/60">No items available.</div>
        ) : items.map((item, i) => {
          const isObj = typeof item === 'object' && item !== null;
          const enText = isObj ? (item.en || '') : String(item);
          const arText = isObj ? (item.ar || '') : '';
          return (
            <div key={i} className="glass p-4 rounded-xl border-border flex flex-col gap-2 hover:border-cyber-cyan/20 transition-colors">
              {enText && <div className="text-sm text-foreground/80 leading-relaxed font-sans">{enText}</div>}
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
    blue: 'text-cyber-blue bg-cyber-blue/10',
    purple: 'text-purple-400 bg-purple-400/10',
    green: 'text-emerald-400 bg-emerald-400/10',
    amber: 'text-amber-400 bg-amber-400/10',
    gray: 'text-white/30 bg-white/5',
  };
  return (
    <div className="glass p-4 rounded-2xl border-white/5">
      <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center mb-2', colors[color] || colors.gray)}>{icon}</div>
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
      className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-mono bg-foreground/5 border border-border text-foreground rounded hover:bg-foreground/10 disabled:opacity-30 disabled:pointer-events-none transition-colors"
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

function _mdToHtml(md) {
  let html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/```sql\n([\s\S]*?)```/g, '<pre class="sql">$1</pre>')
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre>$2</pre>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
  return `<p>${html}</p>`;
}

async function exportReport(doc) {
  let markdown;
  try {
    const resp = await api.report(doc);
    markdown = resp.data?.data?.markdown;
  } catch {
    /* fallback below */
  }
  if (!markdown) {
    markdown = `# ${doc.question || 'DataPilot Report'}\n\n## SQL\n\n\`\`\`sql\n${doc.sql || ''}\n\`\`\`\n`;
  }

  const viz = doc.visualization || {};
  const chartType = viz.chart_type || 'bar';
  const chartSvg = buildChartSVG(doc.results || [], chartType);
  const chartSection = chartSvg
    ? `<h2>Chart (${chartType})</h2><div style="text-align:center;margin:16px 0;">${chartSvg}</div>`
    : '';

  const title = doc.question || 'DataPilot Report';
  const bodyHtml = _mdToHtml(markdown);
  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${title}</title>
<style>
  @page { margin: 20mm; size: A4; }
  body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11pt; line-height: 1.6; color: #1a1a2e; max-width: 210mm; margin: 0 auto; padding: 20px; }
  h1 { font-size: 18pt; border-bottom: 2px solid #2563eb; padding-bottom: 6px; }
  h2 { font-size: 14pt; margin-top: 20px; }
  h3 { font-size: 12pt; }
  pre.sql { background: #f1f5f9; padding: 10px; border-radius: 6px; font-size: 9pt; overflow-x: auto; }
  pre { background: #f8fafc; padding: 8px; border-radius: 4px; font-size: 9pt; }
  code { background: #f1f5f9; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }
  li { margin-left: 20px; }
  p { margin: 8px 0; }
  svg { max-width: 100%; height: auto; }
  .footer { margin-top: 30px; font-size: 9pt; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 10px; }
  @media print { .footer { position: fixed; bottom: 0; width: 100%; } }
</style></head><body>
${bodyHtml}
${chartSection}
<div class="footer">Generated by DataPilot AI — ${new Date().toLocaleString()}</div>
</body></html>`;

  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const w = window.open(url, '_blank');
  if (w) {
    w.focus();
    setTimeout(() => { try { w.print(); } catch {} }, 1000);
  } else {
    const a = document.createElement('a');
    a.href = url;
    a.download = 'datapilot-report.html';
    a.click();
  }
  setTimeout(() => URL.revokeObjectURL(url), 60000);
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
  return String(value).replace(/[<>&"']/g, (char) => ({ '<': '<', '>': '>', '&': '&', '"': '"', "'": '&#39;' }[char]));
}

function buildChartSVG(results = [], chartType = 'bar') {
  if (!results.length) return '';
  const keys = Object.keys(results[0]);
  const strKey = keys.find((key) => typeof results[0][key] === 'string') || null;
  const numKeys = keys.filter((key) => Number.isFinite(Number(results[0][key])));
  const labelKey = strKey || numKeys[0] || keys[0];
  const valueKey = numKeys[0] || keys[0];
  const valueKey2 = numKeys[1] || null;

  if (chartType === 'line' && strKey && numKeys.length >= 1) {
    const labels = results.slice(0, 20).map((row) => String(row[strKey] ?? ''));
    const values = results.slice(0, 20).map((row) => Number(row[numKeys[0]] ?? 0));
    return buildLineSVG(labels, values);
  }
  if (chartType === 'scatter' && numKeys.length >= 2) {
    const xVals = results.slice(0, 50).map((row) => Number(row[numKeys[0]] ?? 0));
    const yVals = results.slice(0, 50).map((row) => Number(row[numKeys[1]] ?? 0));
    return buildScatterSVG(xVals, yVals, numKeys[0], numKeys[1]);
  }
  if (chartType === 'histogram' && numKeys.length >= 1) {
    const values = results.slice(0, 100).map((row) => Number(row[numKeys[0]] ?? 0));
    return buildHistogramSVG(values, numKeys[0]);
  }
  const labels = results.slice(0, 12).map((row) => String(row[labelKey] ?? ''));
  const values = results.slice(0, 12).map((row) => Number(row[valueKey] ?? 0));
  if (chartType === 'pie') return buildPieSVG(labels, values);
  return buildBarSVG(labels, values);
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

function buildLineSVG(labels, values) {
  const width = Math.max(420, labels.length * 60);
  const height = 260;
  const maxVal = Math.max(...values, 1);
  const padX = 40;
  const padY = 20;
  const drawW = width - padX - 20;
  const drawH = height - padY - 40;
  const points = labels.map((label, i) => {
    const x = padX + (i / Math.max(1, labels.length - 1)) * drawW;
    const y = padY + drawH - ((values[i] / maxVal) * drawH);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const dots = labels.map((label, i) => {
    const x = padX + (i / Math.max(1, labels.length - 1)) * drawW;
    const y = padY + drawH - ((values[i] / maxVal) * drawH);
    const skip = labels.length > 15 ? (i % 3 !== 0) : false;
    return skip ? '' : `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" fill="#60A5FA"/>`;
  }).join('');
  const xLabels = labels.filter((_, i) => labels.length > 15 ? i % 3 === 0 : true).map((label, idx, arr) => {
    const origIdx = labels.findIndex((l) => l === label);
    const x = padX + (origIdx / Math.max(1, labels.length - 1)) * drawW;
    return `<text x="${x.toFixed(1)}" y="${height - 8}" font-size="9" text-anchor="end" transform="rotate(-35 ${x.toFixed(1)},${height - 8})" fill="#E5E7EB">${escapeXml(label)}</text>`;
  }).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><rect width="100%" height="100%" fill="#0b1220"/><polyline points="${points}" fill="none" stroke="#60A5FA" stroke-width="2"/>${dots}${xLabels}</svg>`;
}

function buildScatterSVG(xVals, yVals, xLabel, yLabel) {
  const width = 420;
  const height = 260;
  const minX = Math.min(...xVals);
  const maxX = Math.max(...xVals) || 1;
  const minY = Math.min(...yVals);
  const maxY = Math.max(...yVals) || 1;
  const pad = 40;
  const drawW = width - pad - 20;
  const drawH = height - pad - 20;
  const rangeX = maxX - minX || 1;
  const rangeY = maxY - minY || 1;
  const dots = xVals.map((x, i) => {
    const cx = pad + ((x - minX) / rangeX) * drawW;
    const cy = pad + drawH - ((yVals[i] - minY) / rangeY) * drawH;
    return `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="3" fill="#60A5FA" opacity="0.7"/>`;
  }).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><rect width="100%" height="100%" fill="#0b1220"/><text x="20" y="${pad + drawH / 2}" font-size="10" fill="#64748b" transform="rotate(-90 20,${pad + drawH / 2})" text-anchor="middle">${escapeXml(yLabel)}</text><text x="${pad + drawW / 2}" y="${height - 4}" font-size="10" fill="#64748b" text-anchor="middle">${escapeXml(xLabel)}</text>${dots}</svg>`;
}

function buildHistogramSVG(values, columnName) {
  const width = 420;
  const height = 220;
  const bins = 15;
  const min = Math.min(...values);
  const max = Math.max(...values) || 1;
  const range = max - min || 1;
  const binSize = range / bins;
  const counts = Array(bins).fill(0);
  values.forEach((v) => {
    const idx = Math.min(bins - 1, Math.floor((v - min) / binSize));
    counts[idx]++;
  });
  const maxCount = Math.max(...counts, 1);
  const pad = 40;
  const barW = (width - pad - 20) / bins;
  const drawH = height - pad - 20;
  const bars = counts.map((count, i) => {
    const h = Math.round((count / maxCount) * drawH);
    const x = pad + i * barW;
    const y = height - pad - h;
    return `<rect x="${x.toFixed(1)}" y="${y}" width="${Math.max(4, barW - 2)}" height="${h}" fill="#60A5FA" opacity="0.8"/>`;
  }).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><rect width="100%" height="100%" fill="#0b1220"/><text x="20" y="${height / 2}" font-size="10" fill="#64748b" transform="rotate(-90 20,${height / 2})" text-anchor="middle">Count</text><text x="${pad + (width - pad - 20) / 2}" y="${height - 4}" font-size="10" fill="#64748b" text-anchor="middle">${escapeXml(columnName)}</text>${bars}</svg>`;
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