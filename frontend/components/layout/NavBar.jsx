import React from 'react';
import { Link } from 'react-router-dom';
import { FileText } from 'lucide-react';

export default function NavBar() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4" style={{ color: '#1a3c6e' }} />
          <span className="text-sm font-semibold" style={{ color: '#1a3c6e' }}>
            Voter Info Extractor
          </span>
        </div>
        <nav className="flex items-center gap-4 text-sm">
          <Link to="/Home" className="text-slate-600 hover:text-slate-900 transition-colors">Home</Link>
          <Link to="/Upload" className="text-slate-600 hover:text-slate-900 transition-colors">Upload</Link>
        </nav>
      </div>
    </header>
  );
}