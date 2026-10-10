import React, { useState, useEffect } from 'react';
import { X, Calendar, CreditCard, Shield, Zap, FileText, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../services/api';

const EXPENSE_TYPES = [
  { value: 'bill', label: 'Utility Bill (Power, Water, Wi-Fi)', icon: Zap },
  { value: 'emi', label: 'Loan EMI (Car, Home, Personal)', icon: CreditCard },
  { value: 'insurance', label: 'Insurance (Health, Term, Auto)', icon: Shield },
  { value: 'subscription', label: 'Subscription / SIP', icon: Calendar },
  { value: 'rent', label: 'Rent / Maintenance', icon: FileText },
  { value: 'other', label: 'Other Fixed Expense', icon: FileText },
];

const DEFAULT_CATEGORIES = [
  'Bills & Utilities',
  'Rent & Housing',
  'Healthcare',
  'Transportation',
  'Education',
  'Food & Dining',
  'Entertainment',
  'Miscellaneous',
];

const PAYMENT_METHODS = [
  'Auto-Debit',
  'UPI',
  'Net Banking',
  'Credit Card',
  'Debit Card',
  'Cash',
];

export default function RecurringExpenseModal({
  isOpen,
  onClose,
  onSaved,
  item = null,
}) {
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('Bills & Utilities');
  const [amount, setAmount] = useState('');
  const [dueDay, setDueDay] = useState('5');
  const [paymentMethod, setPaymentMethod] = useState('Auto-Debit');
  const [expenseType, setExpenseType] = useState('bill');
  const [notes, setNotes] = useState('');
  const [isActive, setIsActive] = useState(true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (item) {
      setTitle(item.title || '');
      setCategory(item.category || 'Bills & Utilities');
      setAmount(item.amount ? String(item.amount) : '');
      setDueDay(item.due_day ? String(item.due_day) : '5');
      setPaymentMethod(item.payment_method || 'Auto-Debit');
      setExpenseType(item.expense_type || 'bill');
      setNotes(item.notes || '');
      setIsActive(item.is_active !== undefined ? item.is_active : true);
    } else {
      setTitle('');
      setCategory('Bills & Utilities');
      setAmount('');
      setDueDay('5');
      setPaymentMethod('Auto-Debit');
      setExpenseType('bill');
      setNotes('');
      setIsActive(true);
    }
    setError(null);
  }, [item, isOpen]);

  if (!isOpen) return null;

  const handleTypeSelect = (typeVal) => {
    setExpenseType(typeVal);
    if (typeVal === 'bill') setCategory('Bills & Utilities');
    else if (typeVal === 'emi') setCategory('Transportation');
    else if (typeVal === 'insurance') setCategory('Healthcare');
    else if (typeVal === 'rent') setCategory('Rent & Housing');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError('Please provide a title for this monthly expense.');
      return;
    }

    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      setError('Please enter a valid amount greater than zero.');
      return;
    }

    const dayNum = parseInt(dueDay, 10);
    if (isNaN(dayNum) || dayNum < 1 || dayNum > 31) {
      setError('Due day must be between 1 and 31.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        title: title.trim(),
        category,
        amount: numAmount,
        due_day: dayNum,
        payment_method: paymentMethod,
        expense_type: expenseType,
        is_active: isActive,
        notes: notes.trim() || undefined,
      };

      if (item) {
        await api.updateRecurringExpense(item.id, payload);
      } else {
        await api.createRecurringExpense(payload);
      }

      onSaved();
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save monthly common expense.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-navy-900 border border-slate-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 shrink-0">
          <div>
            <h3 className="text-base font-bold text-white tracking-tight">
              {item ? 'Edit Monthly Common Expense' : 'Add Monthly Common Expense'}
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Track fixed commitments (Bills, EMIs, Insurance) that repeat every month
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1">
          {error && (
            <div className="p-3 text-xs rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-start gap-2 animate-in fade-in">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {/* Type Selector Chips */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2">
              Expense Type
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {EXPENSE_TYPES.map((t) => {
                const Icon = t.icon;
                const isSelected = expenseType === t.value;
                return (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => handleTypeSelect(t.value)}
                    className={`p-2.5 rounded-xl border text-left flex items-center gap-2 transition-all ${
                      isSelected
                        ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300 shadow-sm'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                    }`}
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <span className="text-[11px] font-semibold truncate">{t.label.split(' ')[0]}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Title */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Expense Title / Provider
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. HDFC Car Loan EMI, BESCOM Electricity, Star Health"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          {/* Amount & Due Day */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Monthly Amount (₹)
              </label>
              <div className="relative">
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  required
                  placeholder="0.00"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-8 pr-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 font-semibold"
                />
                <span className="absolute left-3.5 top-2.5 text-slate-400 text-sm font-bold">₹</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Due Day (1-31)
              </label>
              <div className="relative">
                <input
                  type="number"
                  min="1"
                  max="31"
                  required
                  value={dueDay}
                  onChange={(e) => setDueDay(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                />
                <Calendar className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              </div>
            </div>
          </div>

          {/* Category & Payment Method */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              >
                {DEFAULT_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Payment Method
              </label>
              <select
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              >
                {PAYMENT_METHODS.map((pm) => (
                  <option key={pm} value={pm}>
                    {pm}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Account / Policy Notes (Optional)
            </label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Loan Acct #8821, Mandate ID, Policy #9923"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          {/* Active Status Toggle */}
          <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
            <div>
              <span className="text-xs font-semibold text-slate-200">
                Active Monthly Commitment
              </span>
              <p className="text-[11px] text-slate-400">
                Include in monthly budget calculations and over-budget warnings
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-10 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
            </label>
          </div>

          {/* Action Buttons */}
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
              className="px-5 py-2.5 text-xs font-bold text-navy-950 bg-emerald-500 hover:bg-emerald-400 rounded-xl transition-all shadow-md shadow-emerald-500/20 disabled:opacity-50"
            >
              {loading ? 'Saving...' : item ? 'Save Changes' : 'Add Monthly Expense'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
