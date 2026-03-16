import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

const STAGES = [
  'Uploading PDF...',
  'Detecting voter cards...',
  'Extracting voter data...',
  'Generating Excel file...',
];

export default function ProcessingProgress({ progress, stageIndex, currentStage }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-6 bg-white rounded-xl border border-slate-200 p-6"
    >
      <div className="flex items-center gap-3 mb-4">
        <Loader2 className="w-5 h-5 animate-spin" style={{ color: '#1a3c6e' }} />
        <span className="text-sm font-semibold" style={{ color: '#1f2937' }}>
          {currentStage || 'Processing...'}
        </span>
        <span className="text-sm font-bold ml-auto" style={{ color: '#1a3c6e' }}>
          {progress}%
        </span>
      </div>

      <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: 'linear-gradient(90deg, #1a3c6e, #2a5ca0)' }}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>

      <div className="mt-4 space-y-2">
        {STAGES.map((stage, i) => (
          <div
            key={i}
            className={`flex items-center gap-2.5 text-xs transition-colors ${
              i < stageIndex ? 'text-green-600' : i === stageIndex ? 'font-medium' : 'text-slate-300'
            }`}
            style={i === stageIndex ? { color: '#1a3c6e' } : undefined}
          >
            <div
              className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                i < stageIndex ? 'bg-green-500' : i === stageIndex ? 'bg-current' : 'bg-slate-200'
              }`}
            />
            {stage}
          </div>
        ))}
      </div>
    </motion.div>
  );
}