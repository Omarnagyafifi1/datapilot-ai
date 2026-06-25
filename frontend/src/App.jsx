import React, { useState, useEffect } from 'react';
import { Layout } from './components/Layout';
import { ChatInterface } from './components/ChatInterface';
import { DataSourceManager } from './components/DataSourceManager';
import { Dashboard } from './components/pages/Dashboard';
import { SchemaViewer } from './components/pages/SchemaViewer';
import { QueryHistory } from './components/pages/QueryHistory';
import { Reports } from './components/pages/Reports';
import { Documentation } from './components/pages/Documentation';
import { Settings } from './components/pages/Settings';
import QueryPage from './query/QueryPage';
import { api } from './lib/api';

function App() {
  const [activeView, setActiveView] = useState('query'); 
  const [dataSources, setDataSources] = useState([]);
  const [selectedSourceId, setSelectedSourceId] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchSources = async () => {
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
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const selectedSource = dataSources.find(s => s.id === selectedSourceId) || null;

  const renderView = () => {
    switch (activeView) {
      case 'query':
        return <QueryPage selectedSourceId={selectedSourceId} selectedSource={selectedSource} />;
      case 'dashboard':
        return <Dashboard onStartAnalyst={() => setActiveView('chat')} />;
      case 'chat':
        return <ChatInterface selectedSourceId={selectedSourceId} selectedSource={selectedSource} />;
      case 'datasources':
        return <DataSourceManager onUpdate={fetchSources} selectedSourceId={selectedSourceId} />;
      case 'schema':
        return <SchemaViewer />;
      case 'history':
        return <QueryHistory />;
      case 'reports':
        return <Reports />;
      case 'documentation':
        return <Documentation />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard onStartAnalyst={() => setActiveView('chat')} />;
    }
  };

  return (
    <Layout 
      activeView={activeView} 
      setActiveView={setActiveView}
      selectedSource={selectedSource}
      selectedSourceId={selectedSourceId}
    >
      {renderView()}
    </Layout>
  );
}

export default App;
