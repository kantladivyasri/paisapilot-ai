import React, { useState, useRef } from 'react';
import { X, UploadCloud, AlertTriangle, CheckCircle, FileText, Download } from 'lucide-react';
import { formatINR } from '../utils/formatters';

export default function CsvImportModal({ isOpen, onClose, onImportSuccess }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      if (!selected.name.endsWith('.csv') && !selected.name.endsWith('.txt')) {
        setError('Please select a valid CSV file.');
        return;
      }
      setFile(selected);
      setError('');
      setResult(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const dropped = e.dataTransfer.files[0];
      if (!dropped.name.endsWith('.csv') && !dropped.name.endsWith('.txt')) {
        setError('Please select a valid CSV file.');
        return;
      }
      setFile(dropped);
      setError('');
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const res = await onImportSuccess(file);
      setResult(res);
    } catch (err) {
      setError(err.message || 'Failed to import CSV');
    } finally {
      setUploading(false);
    }
  };

  const downloadSampleTemplate = () => {
    const csvContent = "data:text/csv;charset=utf-8," + 
      "date,description,amount,type,category\n" +
      "2026-10-01,Monthly Salary,30000.00,income,Salary\n" +
      "2026-10-02,House Rent,7000.00,expense,Rent\n" +
      "2026-10-04,Groceries Blinkit,2500.00,expense,Groceries\n" +
      "2026-10-08,Electricity Bill,1200.00,expense,Electricity\n";
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "nidhipilot_template.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-navy-900 border border-slate-800 rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 shrink-0">
          <div>
            <h3 className="text-base font-bold text-white">Import Transactions via CSV</h3>
            <p className="text-xs text-slate-400">Upload bank exports or digital wallet statements</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-4">
          {error && (
            <div className="p-3 text-xs rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!result ? (
            <>
              {/* Drag & Drop Area */}
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-slate-700 hover:border-emerald-500/50 rounded-2xl p-8 flex flex-col items-center justify-center text-center cursor-pointer bg-slate-950/40 hover:bg-slate-950/70 transition-all group"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.txt"
                  className="hidden"
                  onChange={handleFileChange}
                />
                <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-400 mb-3 group-hover:scale-110 transition-transform">
                  <UploadCloud className="w-8 h-8" />
                </div>
                <p className="text-sm font-semibold text-white mb-1">
                  {file ? file.name : 'Choose a CSV file or drag and drop'}
                </p>
                <p className="text-xs text-slate-400">
                  {file ? `${(file.size / 1024).toFixed(1)} KB` : 'Supports standard Indian bank statements and custom exports'}
                </p>
              </div>

              {/* Supported Columns Guide */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-300">Supported CSV Headers:</span>
                  <button
                    onClick={downloadSampleTemplate}
                    className="text-emerald-400 hover:underline flex items-center gap-1 font-semibold text-[11px]"
                  >
                    <Download className="w-3 h-3" />
                    Download Sample Template
                  </button>
                </div>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  • <b>Description:</b> <code className="text-slate-300">description</code>, <code className="text-slate-300">narration</code>, <code className="text-slate-300">particulars</code><br/>
                  • <b>Amount:</b> <code className="text-slate-300">amount</code>, or separate <code className="text-slate-300">debit</code> / <code className="text-slate-300">credit</code> columns<br/>
                  • <b>Date:</b> <code className="text-slate-300">date</code> (YYYY-MM-DD, DD/MM/YYYY)<br/>
                  • <b>Optional:</b> <code className="text-slate-300">type</code> (income/expense), <code className="text-slate-300">category</code>
                </p>
              </div>
            </>
          ) : (
            /* Results View */
            <div className="space-y-4 animate-in fade-in">
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-emerald-300">{result.message}</h4>
                  <div className="grid grid-cols-3 gap-2 mt-2 text-xs">
                    <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
                      <span className="text-slate-400 block text-[10px]">Imported</span>
                      <span className="text-emerald-400 font-bold text-sm">{result.imported_count}</span>
                    </div>
                    <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
                      <span className="text-slate-400 block text-[10px]">Duplicate Warnings</span>
                      <span className="text-amber-400 font-bold text-sm">{result.duplicate_warning_count}</span>
                    </div>
                    <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
                      <span className="text-slate-400 block text-[10px]">Errors</span>
                      <span className="text-rose-400 font-bold text-sm">{result.error_count}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Duplicate Warnings List */}
              {result.warnings && result.warnings.length > 0 && (
                <div className="border border-amber-500/30 rounded-xl bg-amber-500/5 p-3 text-xs space-y-1.5 max-h-40 overflow-y-auto">
                  <div className="font-semibold text-amber-300 flex items-center gap-1.5 mb-1">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Potential Duplicate Notices (Imported Safely):
                  </div>
                  {result.warnings.map((w, idx) => (
                    <div key={idx} className="text-slate-300 border-b border-amber-500/10 pb-1 text-[11px]">
                      Row {w.row_number}: <b>{w.description}</b> ({formatINR(w.amount)} on {w.date}) — {w.warning}
                    </div>
                  ))}
                </div>
              )}

              {/* Errors List */}
              {result.errors && result.errors.length > 0 && (
                <div className="border border-rose-500/30 rounded-xl bg-rose-500/5 p-3 text-xs space-y-1.5 max-h-40 overflow-y-auto">
                  <div className="font-semibold text-rose-300 flex items-center gap-1.5 mb-1">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Skipped Rows / Errors:
                  </div>
                  {result.errors.map((e, idx) => (
                    <div key={idx} className="text-slate-300 border-b border-rose-500/10 pb-1 text-[11px]">
                      Row {e.row_number}: {e.error}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Action Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-800 shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white rounded-xl transition-colors"
          >
            {result ? 'Done' : 'Cancel'}
          </button>
          {!result && (
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="px-5 py-2 text-xs font-bold text-navy-950 bg-emerald-500 hover:bg-emerald-400 rounded-xl transition-all shadow-md shadow-emerald-500/20 disabled:opacity-50"
            >
              {uploading ? 'Processing CSV...' : 'Import Transactions'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
