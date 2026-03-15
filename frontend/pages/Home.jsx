import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileText, CreditCard, Table2, ArrowRight, Sparkles } from 'lucide-react';
import FeatureCard from '../components/home/FeatureCard';

const features = [
  {
    icon: FileText,
    title: 'Any PDF Supported',
    description: 'Works with any Electoral Roll PDF regardless of number of pages',
  },
  {
    icon: CreditCard,
    title: 'EPIC Number Extraction',
    description: 'Accurately extracts unique voter ID numbers using advanced OCR',
  },
  {
    icon: Table2,
    title: 'Structured Excel Output',
    description: 'Downloads clean Excel file with all voter fields organized',
  },
];

export default function Home() {
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{
          background: 'radial-gradient(ellipse at 50% 0%, rgba(26,60,110,0.06) 0%, transparent 60%)'
        }} />
        <div className="max-w-6xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24 pb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-3xl mx-auto"
          >
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-slate-200 shadow-sm mb-6">
              <Sparkles className="w-3.5 h-3.5" style={{ color: '#f4a020' }} />
              <span className="text-xs font-medium text-slate-600">OCR-Powered Extraction</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-[3.2rem] font-bold leading-tight tracking-tight" style={{ color: '#1a3c6e' }}>
              Electoral Roll Data{' '}
              <span className="relative">
                Extractor
                <svg className="absolute -bottom-1 left-0 w-full" viewBox="0 0 200 8" fill="none">
                  <path d="M2 6C50 2 150 2 198 6" stroke="#f4a020" strokeWidth="3" strokeLinecap="round" />
                </svg>
              </span>
            </h1>

            <p className="mt-5 text-base sm:text-lg leading-relaxed max-w-xl mx-auto" style={{ color: '#6b7280' }}>
              Upload any Electoral Roll PDF and extract complete voter data instantly into a structured Excel file.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                to="/Upload"
                className="inline-flex items-center gap-2 text-white font-semibold px-7 py-3.5 rounded-xl transition-all hover:opacity-90 active:scale-[0.97] shadow-lg"
                style={{ background: '#1a3c6e', boxShadow: '0 4px 20px rgba(26,60,110,0.25)' }}
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section id="how-it-works" className="max-w-6xl mx-auto px-4 sm:px-6 pb-20">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <h2 className="text-2xl sm:text-3xl font-bold" style={{ color: '#1f2937' }}>
            How it works
          </h2>
          <p className="text-sm text-slate-500 mt-2">Three simple steps to extract voter data</p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {features.map((f, i) => (
            <FeatureCard key={f.title} {...f} delay={i * 0.1} />
          ))}
        </div>
      </section>

      {/* About */}
      <section id="about" className="max-w-6xl mx-auto px-4 sm:px-6 pb-20">
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-8 sm:p-12 text-center">
          <h2 className="text-2xl font-bold mb-3" style={{ color: '#1f2937' }}>About</h2>
          <p className="text-sm leading-relaxed max-w-2xl mx-auto" style={{ color: '#6b7280' }}>
            The Voter Information Extractor is designed for government officials and researchers who need to digitize Electoral Roll data efficiently. Our advanced OCR engine processes PDF documents to extract voter information including EPIC numbers, names, addresses, and demographics into a clean, structured Excel format.
          </p>
        </div>
      </section>
    </div>
  );
}