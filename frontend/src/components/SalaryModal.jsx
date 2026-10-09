import React, { useState, useEffect } from 'react';
import { X, Wallet, IndianRupee, TrendingUp, AlertCircle, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';

export default function SalaryModal({
  isOpen,
  onClose,
  currentMonth = '',
  existingSalary = null,
  totalExpenses = 0,
  onSalarySaved,
}) {
  const [month, setMonth] = useState(currentMonth || new Date().toISOString().slice(0, 7));
  const [amount, setAmount] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [liveMetrics, setLiveMetrics] = useState({
    expenses: totalExpenses,
    remaining: 0,
    rate: 0,
  });

  useEffect(() => {
    if (isOpen) {
      const activeMonth = currentMonth || new Date().toISOString().slice(0, 7);
      setMonth(activeMonth);
      if (existingSalary && existingSalary > 0) {
        setAmount(String(existingSalary));
      } else {
        setAmount('');
      }
      setNotes('');
      setError('');
      loadMonthMetrics(activeMonth);
    }
  }, [isOpen, currentMonth, existingSalary]);

  const loadMonthMetrics = async (m) => {
    try {
      const salData = await api.getSalary(m);
      if (salData) {
        if (!amount && salData.amount > 0) {
          setAmount(String(salData.amount));
        }
        if (salData.notes) {
          setNotes(salData.notes);
        }
        setLiveMetrics({
          expenses: salData.total_expenses || 0,
          remaining: salData.remaining_balance || 0,
          rate: salData.savings_rate || 0,
        });
      }
    } catch {
      // Fallback to passed expenses
      setLiveMetrics((prev) => ({ ...prev, expenses: totalExpenses }));
    }
  };

  const handleMonthChange = (e) => {
    const newMonth = e.target.value;
    setMonth(newMonth);
    loadMonthMetrics(newMonth);
  };

  // Compute live preview based on user input
  const numAmount = parseFloat(amount) || 0;
  const computedExpenses = liveMetrics.expenses;
  const computedRemaining = numAmount - computedExpenses;
  const computedRate = numAmount > 0 ? Math.max(0, Math.round(((numAmount - computedExpenses) / numAmount) * 1000) / 10) : 0;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (numAmount <= 0) {
      setError('Please enter a valid salary amount greater than ₹0.');
      return;
    }
    if (!month) {
      setError('Please select a valid month.');
      return;
    }

    setLoading(true);
    try {
      const result = await api.setSalary({
        month,
        amount: numAmount,
        notes: notes.trim() || undefined,
      });
      if (onSalarySaved) {
        onSalarySaved(result);
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to update salary');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-navy-900 border border-slate-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Wallet className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Monthly Salary Management</h3>
              <p className="text-xs text-slate-400">Set real monthly income for accurate cash flow</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 text-xs rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Month & Amount */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Target Month
              </label>
              <input
                type="month"
                required
                value={month}
                onChange={handleMonthChange}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Monthly Salary (₹)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-xs text-slate-500 font-bold">₹</span>
                <input
                  type="number"
                  step="1"
                  min="1"
                  required
                  placeholder="e.g. 50000"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-7 pr-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 font-medium"
                />
              </div>
            </div>
          </div>

          {/* Live Preview Card */}
          <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-2.5">
            <div className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
              Live Balance Impact ({month})
            </div>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="p-2 rounded-lg bg-navy-900 border border-slate-800">
                <span className="text-[10px] text-slate-400 block">Entered Salary</span>
                <span className="text-xs font-bold text-emerald-400">
                  ₹{numAmount.toLocaleString('en-IN')}
                </span>
              </div>
              <div className="p-2 rounded-lg bg-navy-900 border border-slate-800">
                <span className="text-[10px] text-slate-400 block">Logged Expenses</span>
                <span className="text-xs font-bold text-rose-400">
                  ₹{computedExpenses.toLocaleString('en-IN')}
                </span>
              </div>
              <div className="p-2 rounded-lg bg-navy-900 border border-slate-800">
                <span className="text-[10px] text-slate-400 block">Remaining</span>
                <span className={`text-xs font-bold ${computedRemaining >= 0 ? 'text-teal-400' : 'text-rose-400'}`}>
                  ₹{computedRemaining.toLocaleString('en-IN')}
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs pt-1 px-1 text-slate-400">
              <span>Projected Savings Rate:</span>
              <span className={`font-bold ${computedRate >= 20 ? 'text-emerald-400' : 'text-amber-400'}`}>
                {computedRate}%
              </span>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Notes / Source (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. Base Salary, Bonus, Freelance Contract"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-navy-950 bg-emerald-500 hover:bg-emerald-400 rounded-xl transition-all shadow-md shadow-emerald-500/20 disabled:opacity-50"
            >
              <CheckCircle2 className="w-4 h-4" />
              {loading ? 'Saving...' : 'Save Monthly Salary'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
