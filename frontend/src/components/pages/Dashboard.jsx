import React, { useState, useEffect } from 'react';
import { Sparkles, Terminal, ArrowRight, Zap, Database, Loader2, Activity, CheckCircle, BarChart3, PieChart, Clock, Globe } from 'lucide-react';
import { api } from '../../lib/api';

const CHART_COLORS = {
  cyan: '#00f2ff',
  lime: '#ccff00',
  pink: '#ff00ff',
  blue: '#0070ff',
  muted: '#333',
};

function DonutChart({ percent, size = 120, strokeWidth = 8, color = CHART_COLORS.cyan }) {
  const r = (size - strokeWidth) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (percent / 100) * circ;
  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1a1a1a" strokeWidth={strokeWidth} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={strokeWidth}
        strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
        className="transition-all duration-1000 ease-out"
      />
    </svg>
  );
}

function MiniBarChart({ data, height = 120, color = CHART_COLORS.cyan }) {
  if (!data || data.length === 0) return null;
  const maxVal = Math.max(...data.map(d => d.total), 1);
  const barWidth = Math.max(8, Math.min(20, (600 / data.length) - 4));
  const chartWidth = data.length * (barWidth + 4);

  return (
    <svg width={chartWidth} height={height} className="overflow-visible">
      {data.map((d, i) => {
        const barH = (d.total / maxVal) * (height - 20);
        const x = i * (barWidth + 4);
        const y = height - 10 - barH;
        return (
          <g key={d.day}>
            <rect x={x} y={y} width={barWidth} height={barH} fill={color} opacity={0.7} rx={2}
              className="hover:opacity-100 transition-opacity cursor-pointer"
            />
            <rect x={x} y={y} width={barWidth} height={barH * (d.success / (d.total || 1))} fill={CHART_COLORS.lime} opacity={0.9} rx={2} />
            <text x={x + barWidth / 2} y={height - 2} textAnchor="middle" fill="#666" fontSize="7" fontFamily="JetBrains Mono">
              {d.day.slice(5)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function VizBreakdownChart({ data, height = 120 }) {
  if (!data || data.length === 0) {
    return <div className="text-[10px] font-mono text-muted text-center py-8">No visualization data yet</div>;
  }
  const total = data.reduce((s, d) => s + d.count, 0);
  const colors = [CHART_COLORS.cyan, CHART_COLORS.lime, CHART_COLORS.pink, CHART_COLORS.blue, '#888'];
  const segments = data.reduce((acc, d, i) => {
    const prevX = i === 0 ? 0 : acc[i - 1].endX;
    const pct = d.count / total;
    acc.push({ ...d, x: prevX * 100, width: pct * 100, fill: colors[i % colors.length], endX: prevX + pct });
    return acc;
  }, []);

  return (
    <div className="space-y-2">
      <svg width="100%" height={height}>
        {segments.map((s) => (
          <rect key={s.chart_type} x={`${s.x}%`} y="0" width={`${s.width}%`} height={height - 20}
            fill={s.fill} opacity={0.8} rx={4}
          />
        ))}
      </svg>
      <div className="flex flex-wrap gap-3">
        {segments.map((s) => (
          <div key={s.chart_type} className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: s.fill }} />
            <span className="text-[10px] font-mono text-muted uppercase">{s.chart_type}</span>
            <span className="text-[10px] font-mono text-white/60">({s.count})</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricCard({ icon: Icon, label, value, sub, color = 'cyan' }) {
  const colorMap = { cyan: 'text-cyber-cyan', lime: 'text-cyber-lime', pink: 'text-cyber-pink', blue: 'text-cyber-blue' };
  return (
    <div className="glass p-5 rounded-xl border border-white/5 hover:border-white/10 transition-all">
      <div className="flex items-start justify-between mb-3">
        <span className="text-[10px] font-mono text-muted uppercase tracking-wider">{label}</span>
        <Icon size={16} className={`${colorMap[color]} opacity-60`} />
      </div>
      <div className="text-2xl font-bold font-mono tracking-tight">{value}</div>
      {sub && <div className="text-[10px] font-mono text-muted mt-1">{sub}</div>}
    </div>
  );
}

export function Dashboard({ onStartAnalyst, onManageSources, onViewHistory }) {
  const [metrics, setMetrics] = useState(null);
  const [feed, setFeed] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [metricsResp, feedResp] = await Promise.all([
          api.system.metrics(),
          api.system.feed(),
        ]);
        if (metricsResp.data.success) {
          setMetrics(metricsResp.data.data);
        }
        if (feedResp.data.success) {
          setFeed(feedResp.data.data);
        }
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="p-12 max-w-6xl mx-auto flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 size={24} className="animate-spin text-cyber-cyan mb-4" />
        <span className="text-[10px] font-mono text-muted uppercase tracking-widest">Loading neural metrics...</span>
      </div>
    );
  }

  const m = metrics || {};
  const trends = m.trends || [];
  const vizBreakdown = m.visualization_breakdown || [];

  return (
    <div className="p-8 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-2 h-2 rounded-full bg-cyber-cyan animate-pulse shadow-glow-cyan" />
        <span className="text-xs font-mono text-muted uppercase tracking-[0.2em]">Neural Engine Online</span>
      </div>

      <h1 className="text-5xl font-extrabold mb-2 tracking-tighter leading-tight">
        Query <span className="text-cyber-cyan italic">Evaluation</span> Metrics
      </h1>
      <p className="text-base text-muted max-w-xl mb-8">
        Real-time analytics on query performance, visualization generation, and system health.
      </p>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <MetricCard icon={Activity} label="Total Queries" value={m.total_queries ?? 0} color="cyan" />
        <MetricCard icon={Globe} label="Data Sources" value={m.total_sources ?? 0} color="blue" />
        <MetricCard icon={CheckCircle} label="Success Rate" value={`${m.success_rate ?? 0}%`} color="lime" />
        <MetricCard icon={Clock} label="Avg Latency" value={`${m.avg_latency ?? 0}s`} color="pink" />
        <MetricCard icon={BarChart3} label="With Viz" value={`${m.visualization_rate ?? 0}%`}
          sub={`${m.total_visualizations ?? 0} queries`} color="cyan" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="glass p-6 rounded-2xl border border-white/5">
          <h3 className="text-xs font-mono font-bold text-muted uppercase tracking-widest mb-6 flex items-center gap-2">
            <PieChart size={14} /> Query Success Distribution
          </h3>
          <div className="flex items-center justify-center gap-8">
            <div className="relative">
              <DonutChart percent={m.success_rate ?? 0} size={140} strokeWidth={10} color={CHART_COLORS.lime} />
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-lg font-bold font-mono">{m.success_rate ?? 0}%</span>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-cyber-lime" />
                <span className="text-xs font-mono text-muted">Success</span>
                <span className="text-xs font-mono text-white/80">{m.success_rate ?? 0}%</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-cyber-pink" />
                <span className="text-xs font-mono text-muted">Failed</span>
                <span className="text-xs font-mono text-white/80">{100 - (m.success_rate ?? 0)}%</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-cyber-cyan" />
                <span className="text-xs font-mono text-muted">With Viz</span>
                <span className="text-xs font-mono text-white/80">{m.visualization_rate ?? 0}%</span>
              </div>
            </div>
          </div>
        </div>

        <div className="glass p-6 rounded-2xl border border-white/5">
          <h3 className="text-xs font-mono font-bold text-muted uppercase tracking-widest mb-4 flex items-center gap-2">
            <BarChart3 size={14} /> Query Trends (14 days)
          </h3>
          {trends.length > 0 ? (
            <div className="overflow-x-auto pb-2">
              <MiniBarChart data={trends} height={130} />
              <div className="flex items-center gap-4 mt-2">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-sm bg-cyber-lime" />
                  <span className="text-[9px] font-mono text-muted">Success</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-sm bg-cyber-cyan opacity-70" />
                  <span className="text-[9px] font-mono text-muted">Total</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-[10px] font-mono text-muted text-center py-10">No query data in the last 14 days.</div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="glass p-6 rounded-2xl border border-white/5">
          <h3 className="text-xs font-mono font-bold text-muted uppercase tracking-widest mb-4 flex items-center gap-2">
            <BarChart3 size={14} /> Visualization Usage
          </h3>
          <VizBreakdownChart data={vizBreakdown} height={40} />
        </div>

        <div className="glass p-6 rounded-2xl border border-white/5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-mono font-bold text-muted uppercase tracking-widest flex items-center gap-2">
              <Terminal size={14} /> Active Feed
            </h3>
            <span onClick={onViewHistory} className="text-[9px] font-mono text-cyber-cyan underline cursor-pointer">View all</span>
          </div>
          <div className="space-y-2 max-h-[200px] overflow-y-auto no-scrollbar">
            {feed.length === 0 ? (
              <div className="text-[10px] font-mono text-muted text-center py-6">No recent activity detected.</div>
            ) : (
              feed.slice(0, 6).map((item) => (
                <FeedItem key={item.id} type={item.type} content={item.content}
                  time={new Date(item.timestamp).toLocaleTimeString()} />
              ))
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass p-6 rounded-2xl group hover:border-cyber-cyan/20 transition-all cursor-pointer relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
            <Sparkles size={100} />
          </div>
          <div className="w-10 h-10 rounded-xl bg-cyber-cyan/10 flex items-center justify-center text-cyber-cyan mb-4">
            <Zap size={20} />
          </div>
          <h3 className="text-lg font-bold mb-2">Neural Synthesis</h3>
          <p className="text-muted text-xs leading-relaxed mb-4">Execute multi-hop reasoning across your schema to find deep correlations.</p>
          <button onClick={onStartAnalyst}
            className="flex items-center gap-2 text-cyber-cyan font-mono text-[10px] font-bold uppercase tracking-widest hover:gap-4 transition-all">
            Initialize Engine <ArrowRight size={12} />
          </button>
        </div>

        <div className="glass p-6 rounded-2xl group hover:border-cyber-lime/20 transition-all cursor-pointer relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
            <Database size={100} />
          </div>
          <div className="w-10 h-10 rounded-xl bg-cyber-lime/10 flex items-center justify-center text-cyber-lime mb-4">
            <Database size={20} />
          </div>
          <h3 className="text-lg font-bold mb-2">Data Orchestrator</h3>
          <p className="text-muted text-xs leading-relaxed mb-4">Map and connect your distributed databases into a unified knowledge graph.</p>
          <button onClick={onManageSources}
            className="flex items-center gap-2 text-cyber-lime font-mono text-[10px] font-bold uppercase tracking-widest hover:gap-4 transition-all">
            Manage Sources <ArrowRight size={12} />
          </button>
        </div>
      </div>
    </div>
  );
}

function FeedItem({ type, content, time }) {
  const dotColor = type === 'EXECUTION' ? 'bg-cyber-lime' : type === 'ERROR' ? 'bg-cyber-pink' : 'bg-cyber-cyan';
  return (
    <div className="flex items-center justify-between p-3 bg-white/[0.02] border border-white/5 rounded-lg hover:bg-white/[0.04] transition-colors">
      <div className="flex items-center gap-3 min-w-0">
        <div className={`w-1.5 h-1.5 rounded-full ${dotColor} shrink-0`} />
        <div className="min-w-0">
          <p className="text-[9px] font-mono font-bold text-muted uppercase mb-0.5">{type}</p>
          <p className="text-[11px] text-white/70 truncate">{content}</p>
        </div>
      </div>
      <span className="text-[9px] font-mono text-muted shrink-0 ml-2">{time}</span>
    </div>
  );
}
