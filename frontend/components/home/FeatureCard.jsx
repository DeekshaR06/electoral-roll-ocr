import React from 'react';
import { motion } from 'framer-motion';

export default function FeatureCard({ icon: Icon, title, description, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      className="bg-white rounded-xl p-7 shadow-sm hover:shadow-md transition-shadow border border-slate-100"
    >
      <div
        className="w-12 h-12 rounded-xl flex items-center justify-center mb-5"
        style={{ background: 'rgba(244, 160, 32, 0.12)' }}
      >
        <Icon className="w-6 h-6" style={{ color: '#f4a020' }} />
      </div>
      <h3 className="text-lg font-semibold mb-2" style={{ color: '#1f2937' }}>
        {title}
      </h3>
      <p className="text-sm leading-relaxed" style={{ color: '#6b7280' }}>
        {description}
      </p>
    </motion.div>
  );
}