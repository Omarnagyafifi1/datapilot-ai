import React from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

export function Layout({ children, activeView, setActiveView, selectedSource, selectedSourceId }) {
  return (
    <div className="flex h-screen w-full bg-background overflow-hidden text-white/90">
      <Sidebar activeView={activeView} setActiveView={setActiveView} />
      <div className="flex-1 flex flex-col relative overflow-hidden">
        <Header selectedSource={selectedSource} selectedSourceId={selectedSourceId} />
        <main className="flex-1 overflow-hidden relative">
          {/* Subtle Cyber Background Texture */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,#111_0%,#050505_100%)] opacity-50 pointer-events-none" />
          <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'radial-gradient(#fff 1px, transparent 0)', backgroundSize: '40px 40px' }} />
          
          <div className="relative h-full overflow-y-auto no-scrollbar">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
