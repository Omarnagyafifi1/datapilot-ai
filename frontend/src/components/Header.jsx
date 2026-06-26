import React from 'react';
import { Search, Bell, Activity, Grid, User } from 'lucide-react';
import SelectedSourceBadge from './SelectedSourceBadge';

export function Header({ selectedSource, selectedSourceId, dataSources = [], onSelectSource }) {
  return (
    <header className="h-16 border-b border-border flex items-center justify-between px-8 bg-background/50 backdrop-blur-md z-30">
      <div className="flex items-center gap-6 flex-1">
        
        <div className="relative max-w-md w-full group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted group-focus-within:text-cyber-cyan transition-colors" size={16} />
          <input 
            placeholder="Search..."
            className="w-full bg-white/5 border border-white/5 rounded-lg py-2 pl-12 pr-4 text-xs focus:outline-none focus:border-cyber-cyan/50 transition-all font-mono"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-muted font-mono border border-white/10 px-1.5 py-0.5 rounded">CMD+K</div>
        </div>
      </div>

      <div className="flex items-center gap-6">
        {dataSources.length > 0 ? (
          <div className="relative">
            <select
              value={selectedSourceId || ''}
              onChange={(e) => onSelectSource(e.target.value)}
              className="bg-green-600/5 hover:bg-green-600/10 text-cyber-cyan border border-cyber-cyan/30 rounded-full px-4 py-1 text-xs font-mono font-bold outline-none cursor-pointer appearance-none pr-8 transition-all"
              style={{
                backgroundImage: `url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2300f0ff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 8px center',
                backgroundSize: '12px'
              }}
            >
              {dataSources.map((source) => (
                <option key={source.id} value={source.id} className="bg-slate-900 text-white">
                  ● Connected: {source.name}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <SelectedSourceBadge source={selectedSource} />
        )}

        <div className="flex items-center gap-4 text-muted">
          <Bell size={18} className="hover:text-white cursor-pointer transition-colors" />
          <Activity size={18} className="hover:text-white cursor-pointer transition-colors" />
          <Grid size={18} className="hover:text-white cursor-pointer transition-colors" />
          <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center overflow-hidden">
            <User size={20} className="text-white/50" />
          </div>
        </div>
      </div>
    </header>
  );
}
