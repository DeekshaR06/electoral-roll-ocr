import React from 'react';
import { Link, useLocation, Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Users, FileText, UserCheck, UserCheck2, Download, RotateCcw, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import StatsCard from '../components/results/StatsCard';
import VoterTable from '../components/results/VoterTable';
const API_BASE_URL = '/api';

export default function Results() {
  const location = useLocation();
  const results = location.state?.results;

  if (!results) {
    return <Navigate to="/Upload" replace />;
  }

  const { total_voters, total_pages, male_count, female_count, download_id, preview } = results;

  const handleDownload = () => {
    window.location.href = `${API_BASE_URL}/download/${download_id}`;
  };

  const stats = [
    { icon: Users, label: 'Total Voters', value: total_voters?.toLocaleString() || '0', color: '#1a3c6e' },
    { icon: FileText, label: 'Pages Processed', value: total_pages?.toLocaleString() || '0', color: '#f4a020' },
    { icon: UserCheck, label: 'Male Voters', value: male_count?.toLocaleString() || '0', color: '#3b82f6' },
    { icon: UserCheck2, label: 'Female Voters', value: female_count?.toLocaleString() || '0', color: '#ec4899' },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
      {/* Success Banner */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3 p-4 rounded-xl mb-8"
        style={{ background: 'rgba(34, 197, 94, 0.08)', border: '1px solid rgba(34, 197, 94, 0.2)' }}
      >
        <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />
        <div>
          <p className="text-sm font-semibold text-green-800">Extraction Complete</p>
          <p className="text-xs text-green-600 mt-0.5">
            Successfully extracted {total_voters} voter records from {total_pages} pages
          </p>
        </div>
      </motion.div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((s, i) => (
          <StatsCard key={s.label} {...s} delay={i * 0.08} />
        ))}
      </div>

      {/* Preview Table */}
      <div className="mb-8">
        <h2 className="text-lg font-bold mb-4" style={{ color: '#1f2937' }}>
          Preview <span className="text-sm font-normal text-slate-400">(First 10 Records)</span>
        </h2>
        <VoterTable data={preview} />
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-3">
        <Button
          onClick={handleDownload}
          className="flex-1 py-3.5 text-sm font-semibold rounded-xl text-white transition-all hover:opacity-90"
          style={{ background: '#1a3c6e' }}
        >
          <Download className="w-4 h-4 mr-2" />
          Download Excel
        </Button>
        <Link to="/Upload" className="flex-1">
          <Button
            variant="outline"
            className="w-full py-3.5 text-sm font-semibold rounded-xl border-slate-200 hover:bg-slate-50"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Extract Another PDF
          </Button>
        </Link>
      </div>
    </div>
  );
}