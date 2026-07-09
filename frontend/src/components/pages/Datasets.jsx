import { useState, useEffect, useCallback } from 'react';
import { Database, Upload, Search, Trash2, FileText, Table2 } from 'lucide-react';
import { api } from '../../lib/api';
import { UploadZone } from '../UploadZone';
import { UploadPreview } from '../UploadPreview';
import { cn, getErrorMessage } from '../../lib/utils';

export function Datasets({ onSelectSource, onNavigate }) {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState(''); // '', 'csv', 'sqlite'
  const [showUploadZone, setShowUploadZone] = useState(false);
  const [uploadPreview, setUploadPreview] = useState(null);
  const [uploadFile, setUploadFile] = useState(null);
  const [importError, setImportError] = useState(null);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.datasets.list(searchQuery || undefined, selectedType || undefined);
      if (resp.data.success) {
        setDatasets(resp.data.data);
      }
    } catch (err) {
      console.error('Failed to fetch datasets:', err);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedType]);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const handleFileUpload = async (file) => {
    setUploadFile(file);
    setImportError(null);
    
    // Get preview
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const resp = await api.uploads.preview(formData);
      if (resp.data.success) {
        setUploadPreview(resp.data.data);
      }
    } catch (err) {
      setImportError(getErrorMessage(err, 'Failed to preview file'));
    }
  };

  const handleImport = async (options) => {
    if (!uploadFile) return;
    
    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('dataset_name', options.dataset_name || '');
    formData.append('selected_tables', JSON.stringify(options.selected_tables || []));
    formData.append('renamed_columns', JSON.stringify(options.renamed_columns || {}));
    
    try {
      const resp = await api.uploads.import(formData);
      if (resp.data.success) {
        setShowUploadZone(false);
        setUploadPreview(null);
        setUploadFile(null);
        fetchDatasets();
        if (onSelectSource) {
          onSelectSource(resp.data.data.source_id);
        }
        if (onNavigate) {
          onNavigate('chat');
        }
      }
    } catch (err) {
      setImportError(getErrorMessage(err, 'Failed to import file'));
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this dataset?')) return;
    
    try {
      await api.datasets.delete(id);
      fetchDatasets();
    } catch (err) {
      console.error('Failed to delete dataset:', err);
    }
  };

  const handleSelectDataset = (sourceId) => {
    if (onSelectSource) {
      onSelectSource(sourceId);
    }
    if (onNavigate) {
      onNavigate('chat');
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getTypeBadgeClass = (type) => {
    return type === 'sqlite' 
      ? 'bg-cyber-cyan/10 text-cyber-cyan border-cyber-cyan/20' 
      : 'bg-cyber-pink/10 text-cyber-pink border-cyber-pink/20';
  };

  return (
    <div className="p-12 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="mb-12">
        <div className="flex items-center gap-2 text-cyber-cyan mb-4">
          <Database size={20} />
          <span className="text-xs font-mono font-bold uppercase tracking-widest">Dataset Library</span>
        </div>
        <h2 className="text-4xl font-extrabold tracking-tighter mb-4">
          IMPORTED DATASETS<br />
          <span className="text-muted">MANAGED SOURCES</span>
        </h2>
        <p className="text-muted max-w-xl text-sm leading-relaxed">
          Browse, upload, and manage your imported datasets. Each dataset becomes a queryable source for analysis.
        </p>
      </header>

      <div className="space-y-8">
        {/* Controls */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-1">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={16} />
              <input
                type="text"
                placeholder="Search datasets..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-foreground/5 border border-border rounded-lg py-2 pl-10 pr-4 text-xs font-mono text-foreground focus:outline-none focus:border-cyber-cyan/30"
              />
            </div>
            
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-card border border-border rounded-lg px-3 py-2 text-xs font-mono text-foreground focus:outline-none"
            >
              <option value="">All Types</option>
              <option value="csv">CSV</option>
              <option value="sqlite">SQLite</option>
            </select>
          </div>

          <button
            onClick={() => setShowUploadZone(true)}
            className="px-4 py-2 bg-cyber-cyan/10 hover:bg-cyber-cyan/20 border border-cyber-cyan/30 text-cyber-cyan font-mono font-bold text-xs uppercase tracking-widest rounded-lg flex items-center gap-2 transition-all"
          >
            <Upload size={16} /> Upload Dataset
          </button>
        </div>

        {/* Upload Zone Modal */}
        {showUploadZone && (
          <div className="fixed inset-0 bg-background/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
            <div className="glass rounded-2xl border-border p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-mono font-bold text-foreground">
                  Upload Dataset
                </h3>
                <button
                  onClick={() => {
                    setShowUploadZone(false);
                    setUploadPreview(null);
                    setUploadFile(null);
                  }}
                  className="p-2 hover:bg-foreground/5 rounded-lg transition-all"
                >
                  <span className="text-muted text-xs">Cancel</span>
                </button>
              </div>

              {!uploadPreview ? (
                <UploadZone onFileSelect={handleFileUpload} />
              ) : (
                <UploadPreview 
                  preview={uploadPreview} 
                  onImport={handleImport}
                  onCancel={() => {
                    setUploadPreview(null);
                    setUploadFile(null);
                  }}
                />
              )}

              {importError && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-xs font-mono">
                  {importError}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Datasets Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20 text-muted">
            <div className="flex flex-col items-center gap-4">
              <div className="w-8 h-8 border-2 border-cyber-cyan/30 border-t-cyber-cyan rounded-full animate-spin" />
              <span className="text-xs font-mono uppercase tracking-widest">Loading datasets...</span>
            </div>
          </div>
        ) : datasets.length === 0 ? (
          <div className="glass p-12 rounded-2xl border-border text-center">
            <Database size={48} className="opacity-10 mb-4 mx-auto" />
            <p className="text-xs font-mono text-muted uppercase tracking-widest mb-4">
              No datasets imported yet
            </p>
            <button
              onClick={() => setShowUploadZone(true)}
              className="px-4 py-2 bg-cyber-cyan/10 hover:bg-cyber-cyan/20 border border-cyber-cyan/30 text-cyber-cyan font-mono font-bold text-xs uppercase tracking-widest rounded-lg inline-flex items-center gap-2"
            >
              <Upload size={14} /> Upload Your First Dataset
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {datasets.map((dataset) => (
              <div key={dataset.id} className="glass rounded-2xl border-border p-6 hover:border-cyber-cyan/30 transition-all group">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-cyber-cyan/10 border border-cyber-cyan/20 flex items-center justify-center">
                      <FileText size={16} className="text-cyber-cyan" />
                    </div>
                    <span className={cn(
                      "text-[10px] font-mono font-bold px-2 py-0.5 rounded border",
                      getTypeBadgeClass(dataset.source_type)
                    )}>
                      {dataset.source_type.toUpperCase()}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => handleDelete(dataset.id)}
                      className="p-1.5 text-muted hover:text-red-400 hover:bg-foreground/5 rounded"
                      title="Delete"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>

                <h4 className="text-sm font-mono font-bold text-foreground mb-2 truncate">
                  {dataset.name}
                </h4>

                <div className="space-y-2 text-[10px] font-mono text-muted mb-4">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1">
                      <Table2 size={12} />
                      {dataset.table_count} tables
                    </span>
                    <span>{formatFileSize(dataset.file_size)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>{dataset.total_row_count} total rows</span>
                    <span>{dataset.column_count} columns</span>
                  </div>
                </div>

                {dataset.ai_summary && (
                  <p className="text-[9px] text-foreground/60 mb-4 line-clamp-2">
                    {dataset.ai_summary}
                  </p>
                )}

                <button
                  onClick={() => handleSelectDataset(dataset.source_id)}
                  className="w-full py-2 bg-cyber-cyan/10 hover:bg-cyber-cyan/20 border border-cyber-cyan/20 text-cyber-cyan font-mono font-bold text-[10px] uppercase tracking-widest rounded-lg transition-all"
                >
                  Use Dataset
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}