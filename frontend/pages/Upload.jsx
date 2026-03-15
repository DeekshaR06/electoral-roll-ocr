import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import UploadZone from '../components/upload/UploadZone';
import ProcessingProgress from '../components/upload/ProcessingProgress';
const API_BASE_URL = '/api';

export default function Upload() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stageIndex, setStageIndex] = useState(0);
  const pollRef = useRef(null);

  const handleFileSelect = useCallback((f, error) => {
    if (error) {
      setFileError(error);
      setFile(null);
    } else {
      setFile(f);
      setFileError('');
    }
  }, []);

  const handleFileClear = useCallback(() => {
    setFile(null);
    setFileError('');
  }, []);

  const pollStatus = useCallback(() => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/status`);
        if (res.ok) {
          const data = await res.json();
          const pct = data.progress || 0;
          setProgress(pct);
          if (pct < 25) setStageIndex(0);
          else if (pct < 50) setStageIndex(1);
          else if (pct < 75) setStageIndex(2);
          else setStageIndex(3);
        }
      } catch {
        // silently ignore status polling errors
      }
    }, 1000);
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const handleSubmit = async () => {
    if (!file) return;
    setIsProcessing(true);
    setProgress(5);
    setStageIndex(0);
    pollStatus();

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      stopPolling();

      if (!res.ok) {
        const errorData = await res.json().catch(() => null);
        throw new Error(errorData?.detail || 'Processing failed. Please try again.');
      }

      const data = await res.json();
      setProgress(100);
      setStageIndex(3);

      // Brief pause to show 100%
      setTimeout(() => {
        navigate('/Results', { state: { results: data } });
      }, 600);
    } catch (err) {
      stopPolling();
      setIsProcessing(false);
      setProgress(0);
      setStageIndex(0);

      if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        toast.error('Connection failed. Please check if the backend is running and try again.');
      } else if (err.message.includes('Invalid') || err.message.includes('valid')) {
        toast.error('Please upload a valid Electoral Roll PDF.');
      } else {
        toast.error(err.message || 'Processing failed. Please try again.');
      }
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
      <Link
        to="/Home"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-700 transition-colors mb-8"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Home
      </Link>

      <h1 className="text-2xl sm:text-3xl font-bold mb-1" style={{ color: '#1a3c6e' }}>
        Upload Electoral Roll PDF
      </h1>
      <p className="text-sm text-slate-500 mb-8">
        Select your PDF file to begin extraction
      </p>

      <UploadZone
        file={file}
        onFileSelect={handleFileSelect}
        onFileClear={handleFileClear}
        error={fileError}
      />

      <Button
        onClick={handleSubmit}
        disabled={!file || isProcessing}
        className="w-full mt-5 py-3.5 text-sm font-semibold rounded-xl transition-all disabled:opacity-40"
        style={{
          background: file && !isProcessing ? '#1a3c6e' : undefined,
          color: file && !isProcessing ? 'white' : undefined,
        }}
      >
        {isProcessing ? (
          <span className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Processing...
          </span>
        ) : (
          <span className="flex items-center gap-2">
            <Zap className="w-4 h-4" />
            Extract Data
          </span>
        )}
      </Button>

      {isProcessing && (
        <ProcessingProgress progress={progress} stageIndex={stageIndex} />
      )}
    </div>
  );
}