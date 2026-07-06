import { useState, useEffect, useCallback } from 'react';
import { Layout } from './components/Layout';
import ChatInterface from './components/ChatInterface';
import { Analytics } from './components/pages/Analytics';
import { Evaluation } from './components/pages/Evaluation';
import Settings from './components/pages/Settings';
import { QueryHistory } from './components/pages/QueryHistory';
import { Datasets } from './components/pages/Datasets';
import { api } from './lib/api';

function App() {
  const [activeView, setActiveView] = useState('chat');
  const [dataSources, setDataSources] = useState([]);

  // Single source of truth for the active data source, restored from localStorage on load
  const [selectedSourceId, setSelectedSourceIdRaw] = useState(() => {
    return localStorage.getItem('dp_active_source_id') || null;
  });

  const [themeMode, setThemeMode] = useState(() => {
    const saved = localStorage.getItem('dp_theme_mode');
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    const root = document.documentElement;
    if (themeMode === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('dp_theme_mode', themeMode);
  }, [themeMode]);

  // Wrapped setter: updates state AND persists to localStorage, with dev-only logging
  const selectSource = useCallback((id, reason = 'manual', component = 'unknown') => {
    if (import.meta.env.DEV) {
      console.log(`[ActiveSource] -> ${id ?? 'null'} | reason: ${reason} | by: ${component}`);
    }
    setSelectedSourceIdRaw(id);
    if (id) {
      localStorage.setItem('dp_active_source_id', id);
    } else {
      localStorage.removeItem('dp_active_source_id');
    }
  }, []);

  const fetchSources = useCallback(async () => {
    try {
      const resp = await api.datasources.list();
      if (!resp.data.success) return;

      const sources = resp.data.data;
      setDataSources(sources);

      const persistedId = localStorage.getItem('dp_active_source_id');
      const persistedValid = persistedId && sources.some(s => s.id === persistedId);

      if (persistedValid && selectedSourceId !== persistedId) {
        // Restore the saved selection (e.g. right after a page reload)
        selectSource(persistedId, 'restored-on-load', 'App.fetchSources');
      } else if (selectedSourceId && sources.some(s => s.id === selectedSourceId)) {
        // Current selection is still valid — just keep localStorage in sync
        localStorage.setItem('dp_active_source_id', selectedSourceId);
      } else if (sources.length > 0) {
        // Nothing valid selected or persisted — fall back to the first source
        selectSource(
          sources[0].id,
          persistedId ? 'saved-source-no-longer-exists' : 'no-prior-selection',
          'App.fetchSources'
        );
      } else {
        selectSource(null, 'no-sources-available', 'App.fetchSources');
      }
    } catch (err) {
      console.error("Failed to fetch sources", err);
    }
  }, [selectedSourceId, selectSource]);

  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  const selectedSource = dataSources.find(s => s.id === selectedSourceId) || null;

  const renderView = () => {
    switch (activeView) {
      case 'chat':
        return (
          <ChatInterface
            selectedSourceId={selectedSourceId}
            selectedSource={selectedSource}
            dataSources={dataSources}
            onUpdateSources={fetchSources}
            onSelectSource={selectSource}
          />
        );
      case 'history':
        return <QueryHistory />;
      case 'analytics':
        return <Analytics />;
      case 'evaluation':
        return <Evaluation />;
      case 'settings':
        return (
          <Settings
            themeMode={themeMode}
            onChangeTheme={setThemeMode}
          />
        );
      case 'datasets':
        return (
          <Datasets
            onSelectSource={selectSource}
            onNavigate={setActiveView}
          />
        );
      default:
        return (
          <ChatInterface
            selectedSourceId={selectedSourceId}
            selectedSource={selectedSource}
            dataSources={dataSources}
            onUpdateSources={fetchSources}
            onSelectSource={selectSource}
          />
        );
    }
  };

  return (
    <Layout
      activeView={activeView}
      setActiveView={setActiveView}
      selectedSource={selectedSource}
      selectedSourceId={selectedSourceId}
      dataSources={dataSources}
      onSelectSource={selectSource}
      themeMode={themeMode}
      onChangeTheme={setThemeMode}
    >
      {renderView()}
    </Layout>
  );
}

export default App;