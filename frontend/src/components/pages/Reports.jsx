import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, PieChart, Info, Download, Maximize2, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';

export function Reports() {
  const [stats, setStats] = useState({
    total_sources: 0,
    total_queries: 0,
    avg_latency: 0,
    success_rate: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const resp = await api.system.stats();
        if (resp.data.success) {
          setStats(resp.data.data);
        }
      } catch (err) {
        console.error("Failed to fetch stats:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  return (
    <div className="p-12 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="mb-12">
        <div className="flex items-center gap-2 text-cyber-lime mb-4">
          <TrendingUp size={20} />
          <span className="text-xs font-mono font-bold uppercase tracking-widest">Analytics Engine</span>
        </div>
        <h2 className="text-4xl font-extrabold tracking-tighter mb-4">HIGH-FIDELITY<br /><span className="text-cyber-cyan italic">TECHNICAL ANALYSIS.</span></h2>
        <p className="text-muted max-w-xl text-sm leading-relaxed">
          Real-time visualization of synthesized data streams. Neural patterns mapped to multi-dimensional technical reports.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        <div className="lg:col-span-2 glass p-8 rounded-3xl border-white/5 relative overflow-hidden group">
          <div className="flex items-center justify-between mb-8">
            <h4 className="text-[10px] font-mono font-bold text-muted uppercase tracking-[0.2em]">Neural_Cluster_Statistics</h4>
            <div className="flex gap-2">
              <button className="p-2 bg-white/5 rounded-lg text-muted hover:text-white transition-all"><Download size={14} /></button>
              <button className="p-2 bg-white/5 rounded-lg text-muted hover:text-white transition-all"><Maximize2 size={14} /></button>
            </div>
          </div>
          
          <div className="h-64 flex items-end gap-4 relative">
            <Bar height="60%" color="bg-cyber-cyan" label="JAN" />
            <Bar height="40%" color="bg-cyber-pink" label="FEB" />
            <Bar height="85%" color="bg-white/20" label="MAR" />
            <Bar height="65%" color="bg-cyber-cyan" label="APR" />
            <Bar height="50%" color="bg-cyber-lime" label="MAY" />
            <Bar height="75%" color="bg-cyber-pink" label="JUN" />
            
            <div className="absolute inset-x-0 bottom-0 h-px bg-white/10" />
          </div>
        </div>

        <div className="lg:col-span-1 glass p-8 rounded-3xl border-white/5 flex flex-col justify-between">
          <div>
            <h4 className="text-[10px] font-mono font-bold text-muted uppercase tracking-[0.2em] mb-8 text-center">Vector_Distribution</h4>
            <div className="w-48 h-48 mx-auto relative flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border-4 border-white/5" />
              <div className="absolute inset-0 rounded-full border-4 border-cyber-cyan border-t-transparent border-l-transparent rotate-[45deg]" />
              <div className="absolute inset-0 rounded-full border-4 border-cyber-pink border-b-transparent border-r-transparent rotate-[-120deg]" />
              <PieChart size={32} className="text-white/10" />
            </div>
          </div>
          <div className="space-y-4 mt-8">
            <LegendItem color="bg-cyber-cyan" label="Inference" value="64.2%" />
            <LegendItem color="bg-cyber-pink" label="Training" value="28.5%" />
            <LegendItem color="bg-white/10" label="Idle" value="7.3%" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {loading ? (
          <div className="col-span-4 py-10 flex flex-col items-center justify-center text-muted">
            <Loader2 size={24} className="animate-spin mb-4" />
            <span className="text-[10px] font-mono uppercase tracking-widest">Aggregating telemetry...</span>
          </div>
        ) : (
          <>
            <StatCard label="Total Nodes" value={stats.total_sources} sub="Connected" />
            <StatCard label="Total Queries" value={stats.total_queries} sub="Executed" />
            <StatCard label="Avg Latency" value={`${stats.avg_latency}s`} sub="Processing" />
            <StatCard label="Success Rate" value={`${stats.success_rate}%`} sub="Stability" />
          </>
        )}
      </div>
    </div>
  );
}

function Bar({ height, color, label }) {
  return (
    <div className="flex-1 flex flex-col items-center gap-4 group">
      <div 
        className={`w-full ${color} rounded-t-lg transition-all duration-700 relative group-hover:brightness-125`} 
        style={{ height }}
      >
        <div className="absolute -top-8 left-1/2 -translate-x-1/2 text-[10px] font-mono font-bold opacity-0 group-hover:opacity-100 transition-opacity">
          {height}
        </div>
      </div>
      <span className="text-[10px] font-mono text-muted">{label}</span>
    </div>
  );
}

function LegendItem({ color, label, value }) {
  return (
    <div className="flex items-center justify-between text-[10px] font-mono">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${color}`} />
        <span className="text-muted uppercase tracking-widest">{label}</span>
      </div>
      <span className="text-white font-bold">{value}</span>
    </div>
  );
}

function StatCard({ label, value, sub }) {
  return (
    <div className="glass p-6 rounded-2xl border-white/5">
      <p className="text-[10px] font-mono font-bold text-muted uppercase tracking-widest mb-4">{label}</p>
      <div className="flex items-end gap-2">
        <h5 className="text-2xl font-bold tracking-tighter">{value}</h5>
        <span className="text-[10px] font-mono text-muted mb-1">{sub}</span>
      </div>
    </div>
  );
}
