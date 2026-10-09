import React, { useState, useEffect } from 'react';
import { X, Sparkles, CreditCard } from 'lucide-react';
import { api } from '../services/api';

const DEFAULT_CATEGORIES = [
  'Food & Dining',
  'Rent & Housing',
  'Groceries',
  'Transportation',
  'Bills & Utilities',
  'Education',
  'Shopping',
  'Healthcare',
  'Entertainment',
  'Salary / Income',
  'Investments',
  'Miscellaneous',
];

const PAYMENT_METHODS = [
  { value: 'UPI', label: 'UPI (GPay / PhonePe / Paytm)' },
  { value: 'Credit Card', label: 'Credit Card' },
  { value: 'Debit Card', label: 'Debit Card' },
  { value: 'Cash', label: 'Cash' },
  { value: 'Net Banking', label: 'Net Banking / IMPS' },
];

export default function TransactionModal({
  isOpen,
  onClose,
  onSave,
  transaction = null,
  categoriesList = null,
}) {
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [transactionType, setTransactionType] = useState('expense');
  const [category, setCategory] = useState('Food & Dining');
  const [paymentMethod, setPaymentMethod] = useState('UPI');
  const [isEssential, setIsEssential] = useState(false);
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [availableCategories, setAvailableCategories] = useState(DEFAULT_CATEGORIES);

  useEffect(() => {
    if (categoriesList && categoriesList.length > 0) {
      setAvailableCategories(categoriesList.map((c) => (typeof c === 'string' ? c : c.name)));
    } else {
      // Fetch dynamic categories from backend
      api.getCategories().then((cats) => {
        if (cats && cats.length > 0) {
          setAvailableCategories(cats.map((c) => c.name));
        }
      }).catch(() => {});
    }
  }, [categoriesList, isOpen]);

  useEffect(() => {
    if (transaction) {
      setDescription(transaction.description || '');
      setAmount(transaction.amount ? String(transaction.amount) : '');
      setTransactionType(transaction.transaction_type || 'expense');
      setCategory(transaction.category || 'Food & Dining');
      setPaymentMethod(transaction.payment_method || 'UPI');
      setIsEssential(Boolean(transaction.is_essential));
      setDate(transaction.date || new Date().toISOString().split('T')[0]);
      setNotes(transaction.notes || '');
    } else {
      setDescription('');
      setAmount('');
      setTransactionType('expense');
      setCategory('Food & Dining');
      setPaymentMethod('UPI');
      setIsEssential(false);
      setDate(new Date().toISOString().split('T')[0]);
      setNotes('');
    }
    setError('');
  }, [transaction, isOpen]);

  const handleCategoryChange = (newCat) => {
    setCategory(newCat);
    // Auto-check essential based on category name
    const essentialNames = ['rent', 'housing', 'grocery', 'bills', 'utilities', 'education', 'healthcare', 'medical', 'transport'];
    const isAutoEssential = essentialNames.some((kw) => newCat.toLowerCase().includes(kw));
    if (transactionType === 'expense') {
      setIsEssential(isAutoEssential);
    }
  };

  const handleTypeChange = (newType) => {
    setTransactionType(newType);
    if (newType === 'income') {
      setCategory('Salary / Income');
      setIsEssential(false);
    } else {
      setCategory('Food & Dining');
      setIsEssential(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!description.trim()) {
      setError('Please provide a description.');
      return;
    }

    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      setError('Amount must be greater than zero.');
      return;
    }

    if (!date) {
      setError('Please select a valid date.');
      return;
    }

    setSubmitting(true);
    try {
      await onSave({
        description: description.trim(),
        amount: numAmount,
        transaction_type: transactionType,
        category,
        payment_method: paymentMethod,
        is_essential: transactionType === 'expense' ? isEssential : false,
        date,
        notes: notes.trim() || null,
      });
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save transaction');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-navy-900 border border-slate-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <h3 className="text-base font-bold text-white">
            {transaction ? 'Edit Transaction' : 'Add New Transaction'}
          </h3>
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
            <div className="p-3 text-xs rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
              {error}
            </div>
          )}

          {/* Type Toggle */}
          <div className="grid grid-cols-2 gap-2 p-1 bg-slate-950 rounded-xl border border-slate-800">
            <button
              type="button"
              onClick={() => handleTypeChange('expense')}
              className={`py-2 text-xs font-semibold rounded-lg transition-all ${
                transactionType === 'expense'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Expense
            </button>
            <button
              type="button"
              onClick={() => handleTypeChange('income')}
              className={`py-2 text-xs font-semibold rounded-lg transition-all ${
                transactionType === 'income'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Income
            </button>
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Description
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Swiggy Lunch, Metro Pass, Monthly Rent"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          {/* Amount & Date */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Amount (₹)
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                required
                placeholder="0.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Date
              </label>
              <input
                type="date"
                required
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              />
            </div>
          </div>

          {/* Category & Payment Method */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => handleCategoryChange(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              >
                {availableCategories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Payment Method
              </label>
              <select
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              >
                {PAYMENT_METHODS.map((pm) => (
                  <option key={pm.value} value={pm.value}>
                    {pm.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Essential Toggle (Only for expenses) */}
          {transactionType === 'expense' && (
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div>
                <span className="text-xs font-semibold text-slate-200">
                  Essential Expense?
                </span>
                <p className="text-[11px] text-slate-400">
                  Non-negotiable (Rent, Groceries, Utilities, Healthcare)
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={isEssential}
                  onChange={(e) => setIsEssential(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-10 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
              </label>
            </div>
          )}

          {/* Notes */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Notes (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. UPI Ref / Shared with roommate"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
            />
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
              disabled={submitting}
              className="px-5 py-2 text-xs font-bold text-navy-950 bg-emerald-500 hover:bg-emerald-400 rounded-xl transition-all shadow-md shadow-emerald-500/20 disabled:opacity-50"
            >
              {submitting
                ? 'Saving...'
                : transaction
                ? 'Save Changes'
                : transactionType === 'expense'
                ? 'Add Expense'
                : 'Add Income'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
