import React, { useState } from 'react';
import {
  X,
  Bot,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  FileText,
  MessageSquare,
  ArrowRight,
  Trash2,
  Check,
  ShieldAlert,
  Zap,
} from 'lucide-react';
import { api } from '../services/api';

const SAMPLE_SMS_BATCH = `Dear SBI User, your A/C 4532 is debited by Rs 450.00 on 08-Oct-26 by UPI to SWIGGY ref 394857324.
HDFC Bank: Rs. 1,850.00 spent on Credit Card ending 4321 at RELIANCE FRESH on 07-10-2026.
Paid Rs. 240.00 to Uber India via Paytm UPI on 09-Oct-26.
ICICI Bank Alert: INR 65,000.00 credited to Account XX5432 on 01-10-2026. Info: SALARY OCT 2026.
Bescom Electricity: Paid Rs 1,200.00 towards Power Bill on 05-10-2026.`;

const SAMPLE_NATURAL_TEXT = `Paid ₹350 for Zomato dinner yesterday
Sent ₹15,000 to Flat Owner for monthly rent on 02-10-2026
Spent ₹650 on Blinkit groceries today
Received ₹4,500 freelance consulting payment on 06-10-2026`;

export default function SmartImportModal({ isOpen, onClose, onImportSuccess }) {
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState('');
  const [previewData, setPreviewData] = useState(null);
  const [selectedIndices, setSelectedIndices] = useState(new Set());
  const [skipDuplicates, setSkipDuplicates] = useState(true);

  if (!isOpen) return null;

  const handleRunAgent = async () => {
    if (!inputText.trim()) {
      setError('Please paste bank SMS alerts or transaction statements to continue.');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const res = await api.previewImportAgent(inputText.trim());
      if (res.total_detected === 0) {
        setError('No transactions could be parsed. Try pasting SMS messages like "Rs 450 debited at Swiggy" or tabular lines.');
        setPreviewData(null);
      } else {
        setPreviewData(res);
        // Select all non-duplicate items by default
        const nonDups = new Set();
        res.parsed_transactions.forEach((item, idx) => {
          if (!item.is_duplicate) {
            nonDups.add(idx);
          }
        });
        // If all are duplicates or user wants to review all, select all
        setSelectedIndices(nonDups.size > 0 ? nonDups : new Set(res.parsed_transactions.map((_, i) => i)));
      }
    } catch (err) {
      setError(err.message || 'Failed to extract transactions with import agent');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSelect = (idx) => {
    const next = new Set(selectedIndices);
    if (next.has(idx)) {
      next.delete(idx);
    } else {
      next.add(idx);
    }
    setSelectedIndices(next);
  };

  const handleSelectAll = () => {
    if (!previewData) return;
    if (selectedIndices.size === previewData.parsed_transactions.length) {
      setSelectedIndices(new Set());
    } else {
      setSelectedIndices(new Set(previewData.parsed_transactions.map((_, i) => i)));
    }
  };

  const handleCommit = async () => {
    if (!previewData || selectedIndices.size === 0) return;
    setCommitting(true);
    setError('');

    try {
      const itemsToCommit = previewData.parsed_transactions
        .filter((_, idx) => selectedIndices.has(idx))
        .map((p) => ({
          description: p.description,
          amount: p.amount,
          transaction_type: p.transaction_type,
          category: p.category,
          is_essential: p.is_essential,
          date: p.date,
          notes: `Imported via Agent (${p.payment_method || 'Online'})`,
        }));

      const res = await api.commitImportAgent(itemsToCommit, skipDuplicates);
      if (onImportSuccess) {
        onImportSuccess(res);
      }
      handleClose();
    } catch (err) {
      setError(err.message || 'Failed to save imported transactions');
    } finally {
      setCommitting(false);
    }
  };

  const handleClose = () => {
    setInputText('');
    setPreviewData(null);
    setError('');
    setSelectedIndices(new Set());
    onClose();
  };

  const selectedCount = selectedIndices.size;
  const selectedTotal = previewData
    ? previewData.parsed_transactions
        .filter((_, idx) => selectedIndices.has(idx))
        .reduce(
          (acc, cur) => acc + (cur.transaction_type === 'income' ? cur.amount : -cur.amount),
          0
        )
    : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-navy-900 border border-slate-800 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-navy-950/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-navy-950 shadow-md shadow-emerald-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                Automated Transaction Import Agent
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Autonomous Agent
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Paste bank SMS alerts, UPI texts, or statements — the agent automatically extracts, categorizes, and audits for duplicates.
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-5">
          {error && (
            <div className="flex items-center gap-2 p-3 text-xs rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!previewData ? (
            /* Input Step */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300">
                  Paste Bank SMS, UPI Alerts, or Statement Lines
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setInputText(SAMPLE_SMS_BATCH)}
                    className="text-[11px] font-medium px-2.5 py-1 rounded-lg bg-teal-500/10 text-teal-300 border border-teal-500/30 hover:bg-teal-500/20 transition-all flex items-center gap-1.5"
                  >
                    <Sparkles className="w-3 h-3 text-teal-400" />
                    <span>Try Sample Bank SMS</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setInputText(SAMPLE_NATURAL_TEXT)}
                    className="text-[11px] font-medium px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition-all"
                  >
                    Try Natural Text
                  </button>
                </div>
              </div>

              <div className="relative">
                <textarea
                  rows={8}
                  placeholder={`Paste one or more bank notifications here, for example:
• Dear SBI User, your A/C 1234 is debited by Rs 450.00 on 08-Oct-26 by UPI to SWIGGY ref 23498234.
• Paid Rs. 1,850 at RELIANCE FRESH via HDFC Credit Card ending 4321 on 07-10-2026.
• Salary credited: INR 65,000 to Account XX5432 on 01-10-2026.`}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 font-mono leading-relaxed"
                />
                {inputText && (
                  <button
                    type="button"
                    onClick={() => setInputText('')}
                    className="absolute top-2.5 right-2.5 text-[10px] text-slate-500 hover:text-slate-300 px-2 py-0.5 rounded bg-slate-900 border border-slate-800"
                  >
                    Clear
                  </button>
                )}
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400 space-y-1.5">
                <div className="flex items-center gap-1.5 font-semibold text-slate-300 text-[11px]">
                  <Zap className="w-3.5 h-3.5 text-emerald-400" />
                  What the Import Agent handles automatically:
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] pt-1">
                  <div>• Indian bank SMS formats (SBI, HDFC, ICICI, Axis, PNB, etc.)</div>
                  <div>• UPI apps (Google Pay, PhonePe, Paytm, CRED)</div>
                  <div>• Automatic categorization & Essential vs Want tagging</div>
                  <div>• Duplicate detection matching your existing records</div>
                </div>
              </div>
            </div>
          ) : (
            /* Review & Preview Table Step */
            <div className="space-y-4">
              {/* Summary Stats */}
              <div className="grid grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Found</span>
                  <span className="text-base font-black text-white block mt-0.5">
                    {previewData.total_detected} item{previewData.total_detected > 1 ? 's' : ''}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Outflow</span>
                  <span className="text-base font-black text-rose-400 block mt-0.5">
                    ₹{previewData.total_expenses.toLocaleString('en-IN')}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Inflow</span>
                  <span className="text-base font-black text-emerald-400 block mt-0.5">
                    ₹{previewData.total_income.toLocaleString('en-IN')}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Duplicates</span>
                  <span className={`text-base font-black block mt-0.5 ${previewData.duplicate_count > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
                    {previewData.duplicate_count} flagged
                  </span>
                </div>
              </div>

              {/* Table Controls */}
              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={handleSelectAll}
                    className="text-xs text-emerald-400 hover:underline font-medium"
                  >
                    {selectedIndices.size === previewData.parsed_transactions.length ? 'Deselect All' : 'Select All'}
                  </button>
                  <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={skipDuplicates}
                      onChange={(e) => setSkipDuplicates(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-500"
                    />
                    <span>Automatically skip duplicates</span>
                  </label>
                </div>
                <button
                  type="button"
                  onClick={() => setPreviewData(null)}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  ← Edit Source Text
                </button>
              </div>

              {/* Table */}
              <div className="border border-slate-800 rounded-xl overflow-hidden max-h-64 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/90 text-slate-400 uppercase text-[10px] font-semibold sticky top-0 border-b border-slate-800">
                    <tr>
                      <th className="p-3 w-8"></th>
                      <th className="p-3">Date</th>
                      <th className="p-3">Merchant / Payee</th>
                      <th className="p-3">Category</th>
                      <th className="p-3">Classification</th>
                      <th className="p-3 text-right">Amount</th>
                      <th className="p-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 bg-navy-950/40 font-medium">
                    {previewData.parsed_transactions.map((item, idx) => {
                      const isSelected = selectedIndices.has(idx);
                      const isIncome = item.transaction_type === 'income';

                      return (
                        <tr
                          key={idx}
                          className={`hover:bg-slate-800/40 transition-colors ${
                            item.is_duplicate ? 'opacity-70 bg-amber-950/10' : ''
                          }`}
                        >
                          <td className="p-3">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => handleToggleSelect(idx)}
                              className="rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-500 cursor-pointer"
                            />
                          </td>
                          <td className="p-3 text-slate-400 whitespace-nowrap font-mono text-[11px]">
                            {item.date}
                          </td>
                          <td className="p-3 text-white font-semibold">
                            <div>{item.description}</div>
                            {item.payment_method && (
                              <span className="text-[9px] text-slate-500">{item.payment_method}</span>
                            )}
                          </td>
                          <td className="p-3">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              {item.category}
                            </span>
                          </td>
                          <td className="p-3 text-slate-400 text-[11px]">
                            {item.is_essential ? (
                              <span className="text-teal-400 font-semibold">Essential Need</span>
                            ) : (
                              <span className="text-slate-400">Discretionary Want</span>
                            )}
                          </td>
                          <td className={`p-3 text-right font-black whitespace-nowrap text-sm ${isIncome ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isIncome ? '+' : '-'}₹{item.amount.toLocaleString('en-IN')}
                          </td>
                          <td className="p-3 text-center">
                            {item.is_duplicate ? (
                              <span
                                title={item.duplicate_reason || 'Matching transaction already exists'}
                                className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 whitespace-nowrap cursor-help"
                              >
                                ⚠️ Duplicate
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 whitespace-nowrap">
                                ✨ New
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-navy-950/40">
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white transition-colors"
          >
            Cancel
          </button>

          {!previewData ? (
            <button
              type="button"
              disabled={loading || !inputText.trim()}
              onClick={handleRunAgent}
              className="flex items-center gap-2 px-5 py-2 text-xs font-bold text-navy-950 bg-emerald-500 hover:bg-emerald-400 rounded-xl transition-all shadow-md shadow-emerald-500/20 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-navy-950/30 border-t-navy-950 rounded-full animate-spin"></div>
                  <span>Agent Extracting...</span>
                </>
              ) : (
                <>
                  <Bot className="w-4 h-4" />
                  <span>Extract with Agent</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          ) : (
            <button
              type="button"
              disabled={committing || selectedCount === 0}
              onClick={handleCommit}
              className="flex items-center gap-2 px-5 py-2 text-xs font-bold text-navy-950 bg-emerald-500 hover:bg-emerald-400 rounded-xl transition-all shadow-md shadow-emerald-500/20 disabled:opacity-50"
            >
              {committing ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-navy-950/30 border-t-navy-950 rounded-full animate-spin"></div>
                  <span>Saving to Database...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Confirm & Import ({selectedCount} Selected)</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
