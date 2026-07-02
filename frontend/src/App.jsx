import { useState, useEffect, useCallback } from 'react';
import { Layout } from './components/Layout';
import { ChatInterface } from './components/ChatInterface';
import { Analytics } from './components/pages/Analytics';
import { Evaluation } from './components/pages/Evaluation';
import { Settings } from './components/pages/Settings';
import { SchemaViewer } from './components/pages/SchemaViewer';
import { QueryHistory } from './components/pages/QueryHistory';
import { api } from './lib/api';

function App() {
  const [activeView, setActiveView] = useState('chat'); 
  const [dataSources, setDataSources] = useState([]);
  const [selectedSourceId, setSelectedSourceId] = useState(null);
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

  const fetchSources = useCallback(async () => {
    try {
      const resp = await api.datasources.list();
      if (resp.data.success) {
        setDataSources(resp.data.data);
        if (resp.data.data.length > 0 && !selectedSourceId) {
          setSelectedSourceId(resp.data.data[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to fetch sources", err);
    }
  }, [selectedSourceId]);

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
            onSelectSource={setSelectedSourceId}
          />
        );
      case 'schema':
        return (
          <SchemaViewer 
            selectedSourceId={selectedSourceId} 
            selectedSource={selectedSource} 
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
      default:
        return (
          <ChatInterface 
            selectedSourceId={selectedSourceId} 
            selectedSource={selectedSource} 
            dataSources={dataSources}
            onUpdateSources={fetchSources}
            onSelectSource={setSelectedSourceId}
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
      onSelectSource={setSelectedSourceId}
      themeMode={themeMode}
      onChangeTheme={setThemeMode}
    >
      {renderView()}
    </Layout>
  );
}

export default App;
