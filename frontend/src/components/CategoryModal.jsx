import React, { useState, useEffect } from 'react';
import {
  X,
  Tags,
  Plus,
  Trash2,
  Edit2,
  Check,
  AlertTriangle,
  ShoppingBag,
  Utensils,
  Home,
  Car,
  Zap,
  Heart,
  Gift,
  Book,
  Film,
  Dumbbell,
  Coffee,
  Briefcase,
  AlertCircle,
} from 'lucide-react';
import { api } from '../services/api';

const COLOR_PALETTE = [
  '#10b981', // emerald
  '#f97316', // orange
  '#6366f1', // indigo
  '#06b6d4', // cyan
  '#eab308', // yellow
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#ef4444', // red
  '#14b8a6', // teal
  '#84cc16', // lime
  '#64748b', // slate
];

const AVAILABLE_ICONS = [
  { name: 'ShoppingBag', component: ShoppingBag },
  { name: 'Utensils', component: Utensils },
  { name: 'Home', component: Home },
  { name: 'Car', component: Car },
  { name: 'Zap', component: Zap },
  { name: 'Heart', component: Heart },
  { name: 'Gift', component: Gift },
  { name: 'Book', component: Book },
  { name: 'Film', component: Film },
  { name: 'Dumbbell', component: Dumbbell },
  { name: 'Coffee', component: Coffee },
  { name: 'Briefcase', component: Briefcase },
];

export default function CategoryModal({ isOpen, onClose, onCategoriesUpdated }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [editingCategory, setEditingCategory] = useState(null);

  // Form states
  const [name, setName] = useState('');
  const [color, setColor] = useState('#10b981');
  const [icon, setIcon] = useState('ShoppingBag');
  const [isEssential, setIsEssential] = useState(false);
  const [budgetLimit, setBudgetLimit] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadCategories();
      resetForm();
    }
  }, [isOpen]);

  const loadCategories = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getCategories();
      setCategories(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load categories');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setName('');
    setColor('#10b981');
    setIcon('ShoppingBag');
    setIsEssential(false);
    setBudgetLimit('');
    setEditingCategory(null);
    setIsAdding(false);
    setError('');
  };

  const startEdit = (cat) => {
    setEditingCategory(cat);
    setName(cat.name);
    setColor(cat.color || '#10b981');
    setIcon(cat.icon || 'ShoppingBag');
    setIsEssential(Boolean(cat.is_essential));
    setBudgetLimit(cat.budget_limit ? String(cat.budget_limit) : '');
    setIsAdding(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Please provide a category name.');
      return;
    }

    const numLimit = budgetLimit ? parseFloat(budgetLimit) : null;
    if (budgetLimit && (isNaN(numLimit) || numLimit < 0)) {
      setError('Budget limit must be a positive number.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      if (editingCategory) {
        await api.updateCategory(editingCategory.id, {
          name: name.trim(),
          color,
          icon,
          is_essential: isEssential,
          budget_limit: numLimit,
        });
      } else {
        await api.createCategory({
          name: name.trim(),
          color,
          icon,
          is_essential: isEssential,
          budget_limit: numLimit,
        });
      }
      resetForm();
      await loadCategories();
      if (onCategoriesUpdated) onCategoriesUpdated();
    } catch (err) {
      setError(err.message || 'Failed to save category');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (cat) => {
    const confirmMsg = `Delete "${cat.name}"? Any existing transactions under this category will be safely reassigned to "Miscellaneous".`;
    if (!window.confirm(confirmMsg)) return;

    setLoading(true);
    try {
      await api.deleteCategory(cat.id);
      await loadCategories();
      if (onCategoriesUpdated) onCategoriesUpdated();
    } catch (err) {
      setError(err.message || 'Failed to delete category');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-navy-900 border border-slate-800 rounded-2xl w-full max-w-xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400">
              <Tags className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Expense Categories</h3>
              <p className="text-xs text-slate-400">Customize categories, budget caps, and essential tags</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!isAdding && (
              <button
                type="button"
                onClick={() => setIsAdding(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-emerald-500 hover:bg-emerald-400 text-navy-950 transition-colors shadow-sm"
              >
                <Plus className="w-4 h-4" />
                Add Category
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 text-xs rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Form when adding or editing */}
          {isAdding && (
            <form onSubmit={handleSubmit} className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  {editingCategory ? `Edit: ${editingCategory.name}` : 'New Custom Category'}
                </span>
                <button
                  type="button"
                  onClick={resetForm}
                  className="text-xs text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Gym & Fitness"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-navy-900 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Monthly Budget Limit (₹)</label>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    placeholder="Optional, e.g. 3000"
                    value={budgetLimit}
                    onChange={(e) => setBudgetLimit(e.target.value)}
                    className="w-full bg-navy-900 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500"
                  />
                </div>
              </div>

              {/* Color Swatches */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Color Accent</label>
                <div className="flex flex-wrap gap-2">
                  {COLOR_PALETTE.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setColor(c)}
                      className={`w-6 h-6 rounded-full transition-transform ${color === c ? 'scale-125 ring-2 ring-white ring-offset-2 ring-offset-navy-950' : 'hover:scale-110'}`}
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </div>
              </div>

              {/* Essential Toggle */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-navy-900 border border-slate-800">
                <div>
                  <span className="text-xs font-semibold text-slate-200">Essential Need (vs Discretionary Want)</span>
                  <p className="text-[11px] text-slate-400">Classifies expenses in Needs vs Wants analytics</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isEssential}
                    onChange={(e) => setIsEssential(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-teal-500"></div>
                </label>
              </div>

              {/* Save / Cancel */}
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-1.5 text-xs font-bold text-navy-950 bg-teal-400 hover:bg-teal-300 rounded-xl transition-all shadow-sm"
                >
                  {loading ? 'Saving...' : editingCategory ? 'Save Changes' : 'Create Category'}
                </button>
              </div>
            </form>
          )}

          {/* List of categories */}
          <div className="space-y-2">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Configured Categories ({categories.length})
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {categories.map((cat) => (
                <div
                  key={cat.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center gap-2.5 overflow-hidden">
                    <span
                      className="w-3.5 h-3.5 rounded-full shrink-0"
                      style={{ backgroundColor: cat.color || '#10b981' }}
                    />
                    <div className="truncate">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold text-white truncate">{cat.name}</span>
                        {cat.is_essential ? (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                            Need
                          </span>
                        ) : (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0">
                            Want
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                        {cat.budget_limit ? (
                          <span>Limit: ₹{Number(cat.budget_limit).toLocaleString('en-IN')}</span>
                        ) : (
                          <span className="text-slate-500">No cap set</span>
                        )}
                        {cat.current_month_spent > 0 && (
                          <span className="text-teal-400 font-medium">
                            Spent: ₹{Number(cat.current_month_spent).toLocaleString('en-IN')}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0 ml-2">
                    <button
                      type="button"
                      onClick={() => startEdit(cat)}
                      className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                      title="Edit Category"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    {!cat.is_default && (
                      <button
                        type="button"
                        onClick={() => handleDelete(cat)}
                        className="p-1 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                        title="Delete Category"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 flex justify-end bg-navy-950/40">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
