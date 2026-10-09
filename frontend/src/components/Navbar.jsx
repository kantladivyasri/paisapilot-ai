import React from 'react';
import { Plus, RefreshCw, Trash2, SlidersHorizontal, Sparkles } from 'lucide-react';

export default function Navbar({
  activeTab,
  onQuickAdd,
  onSeedDemo,
  onResetDemo,
  onOpenSettings,
  loading,
}) {
  const titles = {
    dashboard: {
      title: 'Financial Dashboard',
      subtitle: 'Overview of income, expenses, cash flow surplus, and financial health',
    },
    transactions: {
      title: 'Transactions & CSV Import',
      subtitle: 'Manage records, filter entries, or import digital bank statements',
    },
    analysis: {
      title: 'AI Spending Analysis',
      subtitle: 'Essential vs discretionary distribution, anomalies, and insights',
    },
    budget: {
      title: 'Personalized Budget Planner',
      subtitle: 'Targeted monthly budgeting, category limits, and deficit recovery plans',
    },
    goals: {
      title: 'Savings Goals',
      subtitle: 'Deterministic timelines and realistic feasibility tracking',
    },
    chat: {
      title: 'AI Finance Assistant',
      subtitle: 'Ask questions grounded directly in your verified financial data',
    },
  };

  const current = titles[activeTab] || titles.dashboard;

  return (
    <header className="h-20 bg-navy-900/60 backdrop-blur-md border-b border-slate-800 px-8 flex items-center justify-between shrink-0 sticky top-0 z-20">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">{current.title}</h2>
        <p className="text-xs text-slate-400 mt-0.5">{current.subtitle}</p>
      </div>

      <div className="flex items-center gap-3">
        {/* Load ₹30k Demo */}
        <button
          onClick={onSeedDemo}
          disabled={loading}
          title="Seed canonical ₹30,000 hackathon demo dataset"
          className="flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-teal-500/10 text-teal-300 border border-teal-500/30 hover:bg-teal-500/20 transition-all disabled:opacity-50"
        >
          <Sparkles className="w-3.5 h-3.5 text-teal-400" />
          <span className="hidden sm:inline">Load Demo Profile</span>
        </button>

        {/* Clear All Data */}
        <button
          onClick={onResetDemo}
          disabled={loading}
          title="Clear all database records to start fresh with your own expenses"
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 border border-slate-800 hover:border-rose-500/30 transition-all disabled:opacity-50"
        >
          <Trash2 className="w-3.5 h-3.5 text-rose-400" />
          <span className="hidden sm:inline">Clear All Data</span>
        </button>

        {/* Quick Add Expense / Income */}
        <button
          onClick={onQuickAdd}
          className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-500 text-navy-950 hover:bg-emerald-400 transition-all shadow-md shadow-emerald-500/20 active:scale-95"
        >
          <Plus className="w-4 h-4 stroke-[2.5]" />
          <span>Add Expense / Income</span>
        </button>
      </div>
    </header>
  );
}
