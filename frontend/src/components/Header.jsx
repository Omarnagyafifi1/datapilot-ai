import React from 'react';
import { Search, Bell, Activity, Grid, User } from 'lucide-react';
import SelectedSourceBadge from './SelectedSourceBadge';

export function Header({ selectedSource }) {
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
        <SelectedSourceBadge source={selectedSource} />

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
