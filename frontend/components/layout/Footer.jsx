import React from 'react';
import { FileText } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4" style={{ color: '#1a3c6e' }} />
          <span className="text-sm font-semibold" style={{ color: '#1a3c6e' }}>
            Voter Info Extractor
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Powered by OCR Technology
        </p>
      </div>
    </footer>
  );
}