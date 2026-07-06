import { useEffect, useState } from 'react';
import { Award, TrendingUp, ThumbsUp, Star, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';

export function Evaluation() {
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function loadEvaluationData() {
      try {
        setLoading(true);
        setError(null);
        const [statsResp, historyResp] = await Promise.all([
          api.system.stats(),
          api.history.list(),
        ]);

        if (!isMounted) return;

        if (statsResp.data.success) {
          setStats(statsResp.data.data);
        }
        if (historyResp.data.success) {
          setHistory(historyResp.data.data || []);
        }
      } catch (err) {
        console.error('Failed to load evaluation data', err);
        if (isMounted) {
          setError('Backend evaluation data is unavailable.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadEvaluationData();

    return () => {
      isMounted = false;
    };
  }, []);

  const totalQueries = stats?.total_queries ?? 0;
  const totalSources = stats?.total_sources ?? 0;
  const avgLatency = stats?.avg_latency ?? 0;
  const successRate = stats?.success_rate ?? 0;
  const successCount = stats?.success_count ?? Math.round((successRate / 100) * totalQueries);
  const failureCount = totalQueries - successCount;

  const benchmarkRows = [
    {
      name: 'Query Success',
      syntax: `${successRate.toFixed(1)}%`,
      performance: `${totalQueries} total`,
      rate: `${successCount} successful`,
      rating: Math.round(Math.min(5, Math.max(0, successRate / 20)) * 100) / 100,
    },
    {
      name: 'Latency Health',
      syntax: `${avgLatency.toFixed(2)}s`,
      performance: totalQueries > 0 ? 'Live backend metric' : 'No queries yet',
      rate: `${failureCount} failures`,
      rating: Math.round((avgLatency <= 1 ? 4.9 : avgLatency <= 2 ? 4.4 : 3.8) * 100) / 100,
    },
    {
      name: 'Source Coverage',
      syntax: `${totalSources}`,
      performance: 'Connected data sources',
      rate: totalSources > 0 ? 'Backend linked' : 'No sources connected',
      rating: totalSources > 0 ? 4.8 : 3.0,
    },
    {
      name: 'History Depth',
      syntax: `${history.length}`,
      performance: 'Tracked queries',
      rate: 'Query archive',
      rating: history.length > 0 ? 4.5 : 3.1,
    },
  ];

  if (loading) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center text-muted min-h-[400px]">
        <Loader2 className="animate-spin text-cyber-cyan mb-4" size={24} />
        <span className="text-xs font-mono uppercase tracking-[0.2em] animate-pulse">Loading evaluation signals...</span>
      </div>
    );
  }

  return (
    <div className="p-12 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="mb-12">
        <div className="flex items-center gap-2 text-cyber-lime mb-4">
          <Award size={20} />
          <span className="text-xs font-mono font-bold uppercase tracking-widest">Model Benchmarks</span>
        </div>
        <h2 className="text-4xl font-extrabold tracking-tighter mb-4">
          EVALUATION<br /><span className="text-muted">.LIVE</span>
        </h2>
        <p className="text-muted max-w-xl text-sm leading-relaxed">
          Assess backend execution health, latency, connected source coverage, and recent query outcomes from the live system.
        </p>
        {error && (
          <div className="mt-4 inline-flex items-center rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
            {error}
          </div>
        )}
      </header>

      {/* Benchmarks Summary Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <EvalMetricCard title="SQL Accuracy Index" score={`${successRate.toFixed(1)}%`} desc="Live success rate" progress={Math.min(100, successRate)} color="cyan" />
        <EvalMetricCard title="Latency Consistency" score={`${avgLatency.toFixed(2)}s`} desc="Average execution latency" progress={Math.max(10, 100 - avgLatency * 20)} color="lime" />
        <EvalMetricCard title="Instruction Following" score={`${totalSources}`} desc="Connected data sources" progress={Math.min(100, totalSources * 20)} color="pink" />
      </div>

      {/* Model Comparisons Table */}
      <div className="glass p-6 rounded-2xl border-border bg-card/40 mb-10">
        <h3 className="text-sm font-mono font-bold text-foreground uppercase tracking-widest mb-6">Live System Comparison</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr className="bg-foreground/5 border-b border-border">
                <th className="px-6 py-4 font-mono font-bold text-xs text-muted uppercase">Metric</th>
                <th className="px-6 py-4 font-mono font-bold text-xs text-muted uppercase">Primary Signal</th>
                <th className="px-6 py-4 font-mono font-bold text-xs text-muted uppercase">Secondary Signal</th>
                <th className="px-6 py-4 font-mono font-bold text-xs text-muted uppercase">Context</th>
                <th className="px-6 py-4 font-mono font-bold text-xs text-muted uppercase">Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {benchmarkRows.map((model, idx) => (
                <tr key={idx} className="hover:bg-foreground/[0.01] transition-colors">
                  <td className="px-6 py-4 font-semibold text-foreground">{model.name}</td>
                  <td className="px-6 py-4 font-mono text-xs text-cyber-cyan">{model.syntax}</td>
                  <td className="px-6 py-4 font-mono text-xs text-muted">{model.performance}</td>
                  <td className="px-6 py-4 font-mono text-xs text-cyber-lime">{model.rate}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5">
                      <Star size={12} className="text-amber-400 fill-amber-400" />
                      <span className="font-mono text-xs text-foreground">{model.rating}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Performance Summary Details */}
        <div className="glass p-6 rounded-2xl border-border bg-card/40">
          <h3 className="text-sm font-mono font-bold text-foreground uppercase tracking-widest mb-6 flex items-center gap-2">
            <TrendingUp size={14} className="text-cyber-lime" /> Performance Summary
          </h3>
          <div className="space-y-4">
            <div className="p-4 bg-foreground/5 border border-border rounded-xl">
              <span className="text-[10px] font-mono font-bold text-cyber-cyan uppercase tracking-widest">Strength</span>
              <p className="text-xs text-foreground/90 mt-1 leading-relaxed">
                <strong>{totalSources > 0 ? 'Connected sources' : 'No connected sources yet'}</strong> are reflected in the live evaluation panel, so the page now mirrors the actual backend state.
              </p>
            </div>
            <div className="p-4 bg-foreground/5 border border-border rounded-xl">
              <span className="text-[10px] font-mono font-bold text-cyber-pink uppercase tracking-widest">Complexity</span>
              <p className="text-xs text-foreground/90 mt-1 leading-relaxed">
                <strong>Query history depth</strong> and execution latency now come from the backend instead of static benchmark fixtures.
              </p>
            </div>
          </div>
        </div>

        {/* Feedback Cards */}
        <div className="glass p-6 rounded-2xl border-border bg-card/40">
          <h3 className="text-sm font-mono font-bold text-foreground uppercase tracking-widest mb-6 flex items-center gap-2">
            <ThumbsUp size={14} className="text-cyber-pink" /> Recent Operator Feedback
          </h3>
          <div className="space-y-4">
            {history.length === 0 ? (
              <div className="text-xs font-mono text-muted uppercase tracking-widest">No recent queries recorded.</div>
            ) : (
              history.slice(0, 3).map((item) => (
                <FeedbackItem
                  key={item.id}
                  operator={item.source_id}
                  model={item.status}
                  comment={item.question}
                  rating={item.status === 'SUCCESS' ? 5 : 3}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function EvalMetricCard({ title, score, desc, progress, color }) {
  const barColors = {
    cyan: 'bg-cyber-cyan',
    lime: 'bg-cyber-lime',
    pink: 'bg-cyber-pink'
  };

  return (
    <div className="glass p-6 rounded-2xl border-border bg-card/50 flex flex-col justify-between hover:border-cyber-cyan/30 transition-colors">
      <div>
        <p className="text-xs font-mono font-bold text-muted uppercase tracking-widest">{title}</p>
        <p className="text-4xl font-extrabold text-foreground mt-2 tracking-tighter">{score}</p>
        <p className="text-[10px] text-muted mt-1">{desc}</p>
      </div>
      <div className="w-full bg-foreground/5 h-1.5 rounded-full mt-6 overflow-hidden">
        <div className={`h-full ${barColors[color]}`} style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}

function FeedbackItem({ operator, model, comment, rating }) {
  return (
    <div className="p-3.5 bg-foreground/[0.01] hover:bg-foreground/[0.02] border border-border rounded-xl transition-all">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono font-bold text-foreground">{operator}</span>
          <span className="text-[9px] font-mono text-muted uppercase">on {model}</span>
        </div>
        <div className="flex items-center gap-0.5">
          {[...Array(rating)].map((_, i) => (
            <Star key={i} size={10} className="text-cyber-lime fill-cyber-lime" />
          ))}
        </div>
      </div>
      <p className="text-xs text-muted leading-relaxed font-sans">{comment}</p>
    </div>
  );
}

export default Evaluation;
