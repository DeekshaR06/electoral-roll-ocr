import React, { useState, useRef, useCallback } from 'react';
import { CloudUpload, FileText, X, AlertCircle } from 'lucide-react';

export default function UploadZone({ file, onFileSelect, onFileClear, error }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) {
      if (dropped.type === 'application/pdf') {
        onFileSelect(dropped);
      } else {
        onFileSelect(null, 'Please upload a valid PDF file.');
      }
    }
  }, [onFileSelect]);

  const handleChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      if (selected.type === 'application/pdf') {
        onFileSelect(selected);
      } else {
        onFileSelect(null, 'Please upload a valid PDF file.');
      }
    }
    e.target.value = '';
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      onClick={() => !file && inputRef.current?.click()}
      className={`
        relative rounded-xl border-2 border-dashed transition-all duration-200 cursor-pointer
        ${file
          ? 'border-green-300 bg-green-50/50'
          : isDragOver
            ? 'border-blue-400 bg-blue-50/50 scale-[1.01]'
            : error
              ? 'border-red-300 bg-red-50/30'
              : 'border-slate-300 bg-white hover:border-slate-400 hover:bg-slate-50/50'
        }
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        onChange={handleChange}
        className="hidden"
      />

      {file ? (
        <div className="flex items-center gap-4 p-6 sm:p-8">
          <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center flex-shrink-0">
            <FileText className="w-6 h-6 text-green-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-800 truncate">{file.name}</p>
            <p className="text-xs text-slate-500 mt-0.5">{formatSize(file.size)}</p>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); onFileClear(); }}
            className="p-2 rounded-lg hover:bg-slate-100 transition-colors flex-shrink-0"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 sm:py-16 px-6">
          <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
            <CloudUpload className="w-8 h-8 text-slate-400" />
          </div>
          <p className="text-sm font-medium text-slate-700 text-center">
            Drag and drop your PDF here or click to browse
          </p>
          <p className="text-xs text-slate-400 mt-1.5">Only .pdf files accepted</p>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 px-6 pb-4 -mt-1">
          <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
          <p className="text-xs text-red-500">{error}</p>
        </div>
      )}
    </div>
  );
}