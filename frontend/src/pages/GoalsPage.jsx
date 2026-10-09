import React, { useState, useEffect } from 'react';
import {
  Target,
  Plus,
  Trash2,
  Edit2,
  CheckCircle2,
  AlertTriangle,
  Calendar,
  Clock,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import { formatINR, formatDate } from '../utils/formatters';
import ConfirmModal from '../components/ConfirmModal';

export default function GoalsPage() {
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingGoal, setEditingGoal] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Form states
  const [name, setName] = useState('');
  const [targetAmount, setTargetAmount] = useState('');
  const [currentAmount, setCurrentAmount] = useState('0');
  const [targetDate, setTargetDate] = useState('2026-12-31');
  const [monthlyContribution, setMonthlyContribution] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  useEffect(() => {
    fetchGoals();
  }, []);

  const fetchGoals = async () => {
    setLoading(true);
    try {
      const data = await api.getGoals();
      setGoals(data || []);
    } catch (err) {
      console.error('Failed to load goals:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAdd = () => {
    setEditingGoal(null);
    setName('');
    setTargetAmount('');
    setCurrentAmount('0');
    setTargetDate('2026-12-31');
    setMonthlyContribution('5000');
    setFormError('');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (g) => {
    setEditingGoal(g);
    setName(g.name);
    setTargetAmount(String(g.target_amount));
    setCurrentAmount(String(g.current_amount));
    setTargetDate(g.target_date);
    setMonthlyContribution(String(g.monthly_contribution));
    setFormError('');
    setIsModalOpen(true);
  };

  const handleSaveGoal = async (e) => {
    e.preventDefault();
    setFormError('');

    const targetVal = parseFloat(targetAmount);
    const currentVal = parseFloat(currentAmount) || 0;
    const monthlyVal = parseFloat(monthlyContribution) || 0;

    if (!name.trim()) {
      setFormError('Please provide a goal name.');
      return;
    }
    if (isNaN(targetVal) || targetVal <= 0) {
      setFormError('Target amount must be greater than zero.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        name: name.trim(),
        target_amount: targetVal,
        current_amount: currentVal,
        target_date: targetDate,
        monthly_contribution: monthlyVal,
      };

      if (editingGoal) {
        await api.updateGoal(editingGoal.id, payload);
      } else {
        await api.createGoal(payload);
      }

      setIsModalOpen(false);
      fetchGoals();
    } catch (err) {
      setFormError(err.message || 'Failed to save savings goal');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.deleteGoal(deleteTarget.id);
      setDeleteTarget(null);
      fetchGoals();
    } catch (err) {
      alert(`Failed to delete goal: ${err.message}`);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-emerald-500/20 border-t-emerald-400 rounded-full animate-spin"></div>
          <span className="text-xs text-slate-400 font-medium">Loading savings goals...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-white">Savings Goals & Milestones</h3>
          <p className="text-xs text-slate-400">
            Deterministic progress tracking and surplus feasibility checks
          </p>
        </div>
        <button
          onClick={handleOpenAdd}
          className="flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl bg-emerald-500 text-navy-950 hover:bg-emerald-400 transition-all shadow-md shadow-emerald-500/20"
        >
          <Plus className="w-4 h-4" />
          <span>New Savings Goal</span>
        </button>
      </div>

      {/* Goals Grid */}
      {goals.length === 0 ? (
        <div className="card-glass rounded-2xl p-12 text-center max-w-md mx-auto space-y-4 border border-dashed border-slate-700">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center mx-auto border border-emerald-500/20">
            <Target className="w-6 h-6" />
          </div>
          <h4 className="text-sm font-bold text-white">No Active Goals Yet</h4>
          <p className="text-xs text-slate-400 leading-relaxed">
            Create milestones for emergency savings, tech gadgets, vehicle down payments, or holiday travel.
          </p>
          <button
            onClick={handleOpenAdd}
            className="px-4 py-2 text-xs font-bold rounded-xl bg-emerald-500 text-navy-950 hover:bg-emerald-400 transition-all"
          >
            Create Your First Goal
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {goals.map((goal) => (
            <div
              key={goal.id}
              className="card-glass card-glass-hover rounded-2xl p-6 flex flex-col justify-between space-y-5 relative overflow-hidden"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h4 className="text-base font-bold text-white truncate">{goal.name}</h4>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => handleOpenEdit(goal)}
                      className="p-1 text-slate-400 hover:text-white rounded-lg transition-colors"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => setDeleteTarget(goal)}
                      className="p-1 text-slate-400 hover:text-rose-400 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <div className="flex items-baseline justify-between mt-3 mb-1.5">
                  <span className="text-2xl font-black text-white">{formatINR(goal.current_amount)}</span>
                  <span className="text-xs text-slate-400 font-medium">of {formatINR(goal.target_amount)}</span>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden mb-2">
                  <div
                    className="bg-emerald-400 h-2.5 rounded-full transition-all"
                    style={{ width: `${Math.min(100, goal.progress_percentage)}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-[11px] text-slate-400 font-semibold">
                  <span>{goal.progress_percentage}% Saved</span>
                  <span>{formatINR(goal.remaining_amount)} Remaining</span>
                </div>
              </div>

              {/* Status & Feasibility Badges */}
              <div className="space-y-2.5 pt-3 border-t border-slate-800 text-xs">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-400 flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> Target Date:
                  </span>
                  <span className="text-slate-200 font-semibold">{formatDate(goal.target_date)}</span>
                </div>

                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> Est. Completion:
                  </span>
                  <span className="text-slate-200 font-semibold">
                    {goal.estimated_months_to_complete !== null
                      ? `${goal.estimated_months_to_complete} months`
                      : 'N/A'}
                  </span>
                </div>

                {/* Feasibility Alert Note */}
                <div
                  className={`p-2.5 rounded-xl border text-[11px] leading-snug flex items-start gap-2 ${
                    goal.is_realistic
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                      : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                  }`}
                >
                  {goal.is_realistic ? (
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
                  )}
                  <span>{goal.feasibility_notes}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit Goal Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-navy-900 border border-slate-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">
                {editingGoal ? 'Edit Savings Goal' : 'Create New Savings Goal'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveGoal} className="p-6 space-y-4">
              {formError && (
                <div className="p-3 text-xs rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
                  {formError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Goal Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Emergency Fund, Laptop, Goa Trip"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Target Amount (₹)</label>
                  <input
                    type="number"
                    min="1"
                    step="100"
                    required
                    value={targetAmount}
                    onChange={(e) => setTargetAmount(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Already Saved (₹)</label>
                  <input
                    type="number"
                    min="0"
                    step="100"
                    value={currentAmount}
                    onChange={(e) => setCurrentAmount(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Target Date</label>
                  <input
                    type="date"
                    required
                    value={targetDate}
                    onChange={(e) => setTargetDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Monthly Plan (₹/mo)</label>
                  <input
                    type="number"
                    min="0"
                    step="100"
                    value={monthlyContribution}
                    onChange={(e) => setMonthlyContribution(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 text-xs font-bold text-navy-950 bg-emerald-500 hover:bg-emerald-400 rounded-xl shadow-md shadow-emerald-500/20 disabled:opacity-50"
                >
                  {submitting ? 'Saving...' : editingGoal ? 'Save Changes' : 'Create Goal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={Boolean(deleteTarget)}
        title="Delete Savings Goal?"
        message={`Are you sure you want to remove "${deleteTarget?.name}"?`}
        confirmText="Confirm Delete"
        confirmType="danger"
        loading={deleting}
        onConfirm={handleDeleteConfirm}
        onClose={() => setDeleteTarget(null)}
      />
    </div>
  );
}
