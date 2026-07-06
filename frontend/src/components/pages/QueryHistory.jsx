import { useState, useEffect } from 'react';
import { Filter, Download, Clock, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';

export function QueryHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const resp = await api.history.list();
        if (resp.data.success) {
          setHistory(resp.data.data);
        }
      } catch (err) {
        console.error("Failed to fetch history:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  return (
    <div className="p-12 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="mb-12 flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 text-cyber-pink mb-4">
            <Clock size={20} />
            <span className="text-xs font-mono font-bold uppercase tracking-widest">Logs</span>
          </div>
          <h2 className="text-4xl font-extrabold tracking-tighter mb-4">QUERY_ARCHIVE<br /><span className="text-muted">.EXE</span></h2>
        </div>
        <div className="flex gap-4">
          <button className="flex items-center gap-2 px-4 py-2 bg-foreground/5 border border-border rounded-xl text-xs font-mono hover:bg-foreground/10 text-foreground transition-all">
            <Filter size={14} /> Filter
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-cyber-lime/10 border border-cyber-lime/20 text-cyber-lime rounded-xl text-xs font-mono font-bold hover:bg-cyber-lime/20 transition-all">
            <Download size={14} /> Export All
          </button>
        </div>
      </header>

      <div className="glass rounded-2xl border-border overflow-hidden">
        <div className="grid grid-cols-12 p-4 border-b border-border bg-foreground/5 text-[10px] font-mono font-bold text-muted uppercase tracking-widest">
          <div className="col-span-5">Query Intent</div>
          <div className="col-span-2 text-center">Status</div>
          <div className="col-span-2 text-center">Latency</div>
          <div className="col-span-3 text-right">Timestamp</div>
        </div>
        
        <div className="divide-y divide-border">
          {loading ? (
            <div className="p-20 flex flex-col items-center justify-center text-muted">
              <Loader2 className="animate-spin mb-4" />
              <p className="text-[10px] font-mono uppercase tracking-widest">Accessing Archive...</p>
            </div>
          ) : history.length === 0 ? (
            <div className="p-20 text-center text-muted text-xs font-mono uppercase tracking-widest">
              No records found in neural buffer.
            </div>
          ) : (
            history.map((item) => (
              <ArchiveItem 
                key={item.id}
                intent={item.question} 
                status={item.status} 
                latency={`${item.latency.toFixed(2)}s`} 
                time={new Date(item.executed_at).toLocaleString()} 
              />
            ))
          )}
        </div>
      </div>

      <div className="mt-8 flex items-center justify-between">
        <div className="text-[10px] font-mono text-muted">Showing {history.length} entries recorded in neural buffer.</div>
        <div className="flex gap-2">
          <button className="w-8 h-8 rounded border border-border flex items-center justify-center text-xs text-muted hover:border-cyber-cyan hover:text-foreground transition-all">1</button>
        </div>
      </div>
    </div>
  );
}

function ArchiveItem({ intent, status, latency, time }) {
  return (
    <div className="grid grid-cols-12 p-5 items-center hover:bg-foreground/5 transition-colors group cursor-pointer">
      <div className="col-span-5 flex items-center gap-4">
        <div className={`w-1.5 h-1.5 rounded-full ${status === 'SUCCESS' ? 'bg-cyber-cyan shadow-[0_0_8px_var(--cyber-cyan)]' : 'bg-red-500'}`} />
        <span className="text-sm text-foreground/80 group-hover:text-foreground transition-colors truncate pr-4">{intent}</span>
      </div>
      <div className="col-span-2 text-center">
        <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border ${status === 'SUCCESS' ? 'bg-cyber-cyan/10 border-cyber-cyan/20 text-cyber-cyan' : 'bg-red-500/10 border-red-500/20 text-red-500'}`}>
          {status}
        </span>
      </div>
      <div className="col-span-2 text-center text-xs font-mono text-muted">{latency}</div>
      <div className="col-span-3 text-right text-xs text-muted font-mono">{time}</div>
    </div>
  );
}
