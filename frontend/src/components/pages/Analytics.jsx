import { useState, useEffect } from 'react';
import { BarChart3, Database, MessageSquare, Clock, CheckCircle2, Terminal, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';

export function Analytics() {
  const [stats, setStats] = useState(null);
  const [feed, setFeed] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError(null);
        const [statsResp, feedResp] = await Promise.all([
          api.system.stats(),
          api.system.feed()
        ]);
        
        if (statsResp.data.success) {
          setStats(statsResp.data.data);
        }
        if (feedResp.data.success) {
          setFeed(feedResp.data.data);
        }
      } catch (err) {
        console.error("Failed to load analytics data", err);
        setError('Backend analytics data is unavailable.');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center text-muted min-h-[400px]">
        <Loader2 className="animate-spin text-cyber-cyan mb-4" size={24} />
        <span className="text-xs font-mono uppercase tracking-[0.2em] animate-pulse">Initializing analytics metrics...</span>
      </div>
    );
  }

  const totalSources = stats?.total_sources ?? 0;
  const totalQueries = stats?.total_queries ?? 0;
  const avgLatency = stats?.avg_latency ?? 0;
  const successRate = stats?.success_rate ?? 0;

  return (
    <div className="p-12 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="mb-12">
        <div className="flex items-center gap-2 text-cyber-cyan mb-4">
          <BarChart3 size={20} />
          <span className="text-xs font-mono font-bold uppercase tracking-widest">Platform Insights</span>
        </div>
        <h2 className="text-4xl font-extrabold tracking-tighter mb-4">
          ANALYTICS<br /><span className="text-muted">.DASHBOARD</span>
        </h2>
        <p className="text-muted max-w-xl text-sm leading-relaxed">
          Monitor neural engine query volumes, execution latency trends, database connection metrics, and system activity logs.
        </p>
        {error && (
          <div className="mt-4 inline-flex items-center rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
            {error}
          </div>
        )}
      </header>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
        <MetricCard icon={<MessageSquare size={18} />} label="Total Queries" value={totalQueries} color="cyan" trend="+14% this week" />
        <MetricCard icon={<Database size={18} />} label="Data Sources" value={totalSources} color="lime" trend="All connected" />
        <MetricCard icon={<Clock size={18} />} label="Avg Latency" value={`${avgLatency.toFixed(2)}s`} color="purple" trend="-0.15s improvement" />
        <MetricCard icon={<CheckCircle2 size={18} />} label="Success Rate" value={`${successRate.toFixed(1)}%`} color="green" trend="Stable" />
      </div>

      {/* SVG Charts Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
        {/* Latency & Volume Chart */}
        <div className="lg:col-span-2 glass p-6 rounded-2xl border-border bg-card/40">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-sm font-mono font-bold text-foreground uppercase tracking-widest">Query Volume over Time</h3>
              <p className="text-[10px] text-muted">Daily query processing aggregates</p>
            </div>
            <div className="flex items-center gap-4 text-[10px] font-mono">
              <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-cyber-cyan/30 border border-cyber-cyan rounded" /> Queries</div>
              <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-cyber-pink/30 border border-cyber-pink rounded" /> Target</div>
            </div>
          </div>
          
          <div className="h-56 w-full flex items-end">
            <svg className="w-full h-full" viewBox="0 0 600 200" preserveAspectRatio="none">
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--cyber-cyan)" stopOpacity="0.2" />
                  <stop offset="100%" stopColor="var(--cyber-cyan)" stopOpacity="0.0" />
                </linearGradient>
              </defs>
              {/* Grid Lines */}
              <line x1="0" y1="50" x2="600" y2="50" stroke="var(--border)" strokeOpacity="0.3" strokeDasharray="4 4" />
              <line x1="0" y1="100" x2="600" y2="100" stroke="var(--border)" strokeOpacity="0.3" strokeDasharray="4 4" />
              <line x1="0" y1="150" x2="600" y2="150" stroke="var(--border)" strokeOpacity="0.3" strokeDasharray="4 4" />
              
              {/* Area Area */}
              <path d="M 0 170 Q 100 130 200 150 T 400 90 T 600 50 L 600 200 L 0 200 Z" fill="url(#areaGrad)" />
              {/* Line Area */}
              <path d="M 0 170 Q 100 130 200 150 T 400 90 T 600 50" fill="none" stroke="var(--cyber-cyan)" strokeWidth="2.5" />
              {/* Dot Markers */}
              <circle cx="200" cy="150" r="4.5" fill="var(--background)" stroke="var(--cyber-cyan)" strokeWidth="2" />
              <circle cx="400" cy="90" r="4.5" fill="var(--background)" stroke="var(--cyber-cyan)" strokeWidth="2" />
              <circle cx="600" cy="50" r="4.5" fill="var(--background)" stroke="var(--cyber-cyan)" strokeWidth="2" />
            </svg>
          </div>
          
          <div className="flex items-center justify-between font-mono text-[9px] text-muted mt-3 px-1">
            <span>MON</span>
            <span>TUE</span>
            <span>WED</span>
            <span>THU</span>
            <span>FRI</span>
            <span>SAT</span>
            <span>SUN</span>
          </div>
        </div>

        {/* Model Distribution */}
        <div className="glass p-6 rounded-2xl border-border bg-card/40 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-mono font-bold text-foreground uppercase tracking-widest mb-1">Model Distribution</h3>
            <p className="text-[10px] text-muted">Core LLM dispatch shares</p>
          </div>

          <div className="flex items-center justify-center py-4">
            {/* Donut SVG Chart */}
            <div className="relative w-36 h-36">
              <svg width="100%" height="100%" viewBox="0 0 42 42" className="transform -rotate-90">
                <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--border)" strokeOpacity="0.3" strokeWidth="4.5" />
                
                {/* Llama 3 - 50% */}
                <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--cyber-cyan)" strokeWidth="4.5" strokeDasharray="50 50" strokeDashoffset="0" />
                {/* Claude - 30% */}
                <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--cyber-pink)" strokeWidth="4.5" strokeDasharray="30 70" strokeDashoffset="-50" />
                {/* Gemini - 20% */}
                <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--cyber-lime)" strokeWidth="4.5" strokeDasharray="20 80" strokeDashoffset="-80" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-[10px] font-mono text-muted uppercase">Llama 3</span>
                <span className="text-lg font-bold text-foreground">50%</span>
              </div>
            </div>
          </div>

          <div className="space-y-2 mt-2">
            <LegendItem color="bg-cyber-cyan" label="Llama 3 (Groq)" value="50%" />
            <LegendItem color="bg-cyber-pink" label="Claude 3.5 (Anthropic)" value="30%" />
            <LegendItem color="bg-cyber-lime" label="Gemini 2.5 (Google)" value="20%" />
          </div>
        </div>
      </div>

      {/* Activity Logs Feed */}
      <div className="glass p-6 rounded-2xl border-border bg-card/40">
        <h3 className="text-sm font-mono font-bold text-foreground uppercase tracking-widest mb-6 flex items-center gap-2">
          <Terminal size={14} className="text-cyber-pink" /> Activity Stream
        </h3>

        <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2">
          {feed.length === 0 ? (
            <div className="text-center py-8 text-xs font-mono text-muted uppercase">No queries processed recently.</div>
          ) : (
            feed.map((item) => (
              <div key={item.id} className="flex items-center justify-between p-3.5 bg-foreground/[0.01] hover:bg-foreground/[0.02] border border-border rounded-xl transition-all">
                <div className="flex items-center gap-4">
                  <div className={`w-2 h-2 rounded-full ${item.type === 'ERROR' ? 'bg-red-400' : 'bg-cyber-cyan'}`} />
                  <div>
                    <span className="text-[9px] font-mono font-bold text-muted uppercase tracking-widest">{item.type}</span>
                    <p className="text-xs text-foreground/90 mt-0.5 leading-relaxed">{item.content}</p>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-muted shrink-0 ml-4">
                  {new Date(item.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, color, trend }) {
  const colors = {
    cyan: 'text-cyber-cyan bg-cyber-cyan/10 border-cyber-cyan/20',
    lime: 'text-cyber-lime bg-cyber-lime/10 border-cyber-lime/20',
    purple: 'text-cyber-blue bg-cyber-blue/10 border-cyber-blue/20',
    green: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'
  };

  return (
    <div className="glass p-6 rounded-2xl border-border bg-card/50 flex flex-col justify-between hover:border-cyber-cyan/30 transition-colors">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-2.5 rounded-xl border ${colors[color]}`}>{icon}</div>
        <span className="text-[9px] font-mono text-muted uppercase tracking-widest">{trend}</span>
      </div>
      <div>
        <p className="text-xs font-bold text-muted uppercase tracking-wider">{label}</p>
        <p className="text-3xl font-extrabold text-foreground mt-1.5 tracking-tighter">{value}</p>
      </div>
    </div>
  );
}

function LegendItem({ color, label, value }) {
  return (
    <div className="flex items-center justify-between text-[10px] font-mono">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${color}`} />
        <span className="text-muted">{label}</span>
      </div>
      <span className="font-bold text-foreground">{value}</span>
    </div>
  );
}

export default Analytics;
