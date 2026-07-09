import { useState, useCallback } from 'react';
import { Upload, FileText, Database, AlertCircle } from 'lucide-react';
import { cn } from '../lib/utils';

export function UploadZone({ onFileSelect }) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState(null);

  const validateAndSelect = useCallback((file) => {
    setError(null);
    
    // Validate extension
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['csv', 'db', 'sqlite', 'sqlite3'].includes(ext)) {
      setError('Unsupported file type. Please upload CSV or SQLite files.');
      return;
    }
    
    onFileSelect(file);
  }, [onFileSelect]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      validateAndSelect(files[0]);
    }
  }, [validateAndSelect]);

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      validateAndSelect(files[0]);
    }
  };

  return (
    <div
      className={cn(
        "border-2 border-dashed rounded-xl p-8 text-center transition-all",
        isDragging 
          ? "border-cyber-cyan bg-cyber-cyan/5" 
          : "border-border hover:border-cyber-cyan/50"
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="flex flex-col items-center gap-4">
        <div className={cn(
          "w-16 h-16 rounded-full flex items-center justify-center transition-all",
          isDragging ? "bg-cyber-cyan/20" : "bg-foreground/5"
        )}>
          <Upload size={32} className={isDragging ? "text-cyber-cyan" : "text-muted"} />
        </div>

        <div>
          <p className="text-sm font-mono font-bold text-foreground mb-2">
            Drop your dataset file here
          </p>
          <p className="text-xs font-mono text-muted">
            Or click to browse from your computer
          </p>
        </div>

        <div className="flex items-center gap-4 text-[10px] font-mono text-muted">
          <span className="flex items-center gap-1">
            <FileText size={12} /> CSV
          </span>
          <span className="flex items-center gap-1">
            <Database size={12} /> SQLite (.db, .sqlite)
          </span>
        </div>

        <input
          type="file"
          id="dataset-upload"
          className="hidden"
          accept=".csv,.db,.sqlite,.sqlite3"
          onChange={handleFileChange}
        />
        <label
          htmlFor="dataset-upload"
          className="px-4 py-2 bg-cyber-cyan/10 hover:bg-cyber-cyan/20 border border-cyber-cyan/30 text-cyber-cyan font-mono font-bold text-xs uppercase tracking-widest rounded-lg cursor-pointer transition-all"
        >
          Browse Files
        </label>

        {error && (
          <div className="flex items-center gap-2 text-red-400 text-xs font-mono mt-2">
            <AlertCircle size={14} />
            {error}
          </div>
        )}
      </div>
    </div>
  );
}