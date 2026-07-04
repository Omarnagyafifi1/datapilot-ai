import { useState } from 'react';
import { CheckCircle, AlertCircle, FileText, Table2, BarChart3 } from 'lucide-react';

export function UploadPreview({ preview, onImport, onCancel }) {
  const [datasetName, setDatasetName] = useState(preview?.filename?.split('.')[0] || '');
  const [selectedTables, setSelectedTables] = useState(
    preview?.tables?.map(t => t.name) || []
  );

  const handleTableToggle = (tableName) => {
    setSelectedTables(prev => 
      prev.includes(tableName)
        ? prev.filter(t => t !== tableName)
        : [...prev, tableName]
    );
  };

  const handleImport = () => {
    onImport({
      dataset_name: datasetName,
      selected_tables: selectedTables,
    });
  };

  const formatNumber = (num) => {
    return new Intl.NumberFormat().format(num);
  };

  const getQualityColor = () => {
    const { quality_report } = preview || {};
    if (!quality_report) return 'text-muted';
    
    if (quality_report.has_nulls || quality_report.has_duplicates) {
      return 'text-yellow-400';
    }
    return 'text-cyber-lime';
  };

  return (
    <div className="space-y-6">
      {/* File Info */}
      <div className="glass p-4 rounded-xl border-border">
        <div className="flex items-center gap-3 mb-3">
          <FileText size={16} className="text-cyber-cyan" />
          <span className="text-xs font-mono font-bold text-foreground">File Information</span>
        </div>
        
        <div className="space-y-2 text-[10px] font-mono">
          <div className="flex items-between justify-between">
            <span className="text-muted">Filename:</span>
            <span className="text-foreground">{preview.filename}</span>
          </div>
          <div className="flex items-between justify-between">
            <span className="text-muted">Type:</span>
            <span className="text-cyber-cyan">{preview.detected_format.toUpperCase()}</span>
          </div>
          <div className="flex items-between justify-between">
            <span className="text-muted">Size:</span>
            <span className="text-foreground">{formatNumber(preview.file_size)} bytes</span>
          </div>
        </div>
      </div>

      {/* Dataset Name */}
      <div>
        <label className="text-[10px] font-mono font-bold text-muted uppercase mb-2 block">
          Dataset Name
        </label>
        <input
          type="text"
          value={datasetName}
          onChange={(e) => setDatasetName(e.target.value)}
          className="w-full bg-foreground/5 border border-border rounded-lg px-3 py-2 text-xs font-mono text-foreground focus:outline-none focus:border-cyber-cyan/30"
          placeholder="Enter a name for this dataset"
        />
      </div>

      {/* Tables Selector (for SQLite) */}
      {preview.tables && preview.tables.length > 0 && (
        <div>
          <div className="flex items-center gap-2 text-cyber-cyan mb-3">
            <Table2 size={14} />
            <span className="text-[10px] font-mono font-bold uppercase tracking-widest">Tables ({preview.tables.length})</span>
          </div>
          
          <div className="space-y-2 max-h-48 overflow-y-auto no-scrollbar">
            {preview.tables.map((table) => (
              <div key={table.name} className="glass rounded-lg p-3 border-border">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id={`table-${table.name}`}
                      checked={selectedTables.includes(table.name)}
                      onChange={() => handleTableToggle(table.name)}
                      className="w-3 h-3 accent-cyber-cyan"
                    />
                    <label htmlFor={`table-${table.name}`} className="text-xs font-mono font-bold text-foreground cursor-pointer">
                      {table.name}
                    </label>
                  </div>
                  <span className="text-[9px] font-mono text-muted">{table.row_count} rows</span>
                </div>
                
                <div className="text-[9px] font-mono text-muted space-y-1 pl-4">
                  {table.columns.slice(0, 5).map((col) => (
                    <div key={col.name} className="flex items-center justify-between">
                      <span className="truncate">{col.name}</span>
                      <span className="text-cyber-cyan/70">{col.data_type}</span>
                    </div>
                  ))}
                  {table.columns.length > 5 && (
                    <span className="text-muted">+{table.columns.length - 5} more columns</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quality Report */}
      {preview.quality_report && (
        <div>
          <div className="flex items-center gap-2 text-cyber-cyan mb-3">
            <BarChart3 size={14} />
            <span className="text-[10px] font-mono font-bold uppercase tracking-widest">Data Quality</span>
          </div>
          
          <div className="glass rounded-lg p-3 border-border">
            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
              <div className="flex flex-col">
                <span className="text-muted">Total Rows</span>
                <span className="text-foreground">{formatNumber(preview.quality_report.total_rows)}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-muted">Total Columns</span>
                <span className="text-foreground">{preview.quality_report.total_columns}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-muted">Missing Values</span>
                <span className={getQualityColor()}>
                  {Object.keys(preview.quality_report.missing_values).length} columns with nulls
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-muted">Duplicates</span>
                <span className={getQualityColor()}>
                  {preview.quality_report.duplicate_rows} rows
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Relationships (for SQLite) */}
      {preview.relationships && preview.relationships.length > 0 && (
        <div>
          <div className="flex items-center gap-2 text-cyber-cyan mb-3">
            <span className="text-[10px] font-mono font-bold uppercase tracking-widest">Relationships</span>
          </div>
          
          <div className="glass rounded-lg p-3 border-border">
            {preview.relationships.map((rel, idx) => (
              <div key={idx} className="text-[9px] font-mono text-muted py-1">
                {rel.column} → {rel.referenced_table}.{rel.referenced_column}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Duplicate Warning */}
      {preview.is_duplicate && (
        <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg flex items-start gap-2">
          <AlertCircle size={14} className="text-yellow-400 mt-0.5" />
          <div className="text-[10px] font-mono text-yellow-400">
            <span className="font-bold">Duplicate Detected:</span> This file appears to be a duplicate of '{preview.existing_dataset?.name}'.
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <button
          onClick={handleImport}
          className="flex-1 py-2 bg-cyber-cyan text-background font-mono font-bold text-xs uppercase tracking-widest rounded-lg flex items-center justify-center gap-2 hover:brightness-110 transition-all"
        >
          <CheckCircle size={14} /> Import Dataset
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 border border-border text-muted font-mono font-bold text-xs uppercase tracking-widest rounded-lg hover:text-foreground hover:bg-foreground/5 transition-all"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}