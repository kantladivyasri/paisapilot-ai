import React from 'react';
import { Plus, Trash2, Sparkles, Bot } from 'lucide-react';
import NotificationBell from './NotificationBell';

export default function Navbar({
  activeTab,
  onQuickAdd,
  onOpenSmartImport,
  onSeedDemo,
  onResetDemo,
  onOpenSettings,
  loading,
  refreshKey,
}) {
  const titles = {
    dashboard: {
      title: 'Money Overview',
      subtitle: 'See your salary, expenses, and money left to spend at a glance',
    },
    transactions: {
      title: 'Expenses & Income History',
      subtitle: 'Add, search, edit transactions, or import your bank statement',
    },
    analysis: {
      title: 'Spending Insights',
      subtitle: 'Simple breakdown of needs vs wants, daily habits, and spending trends',
    },
    budget: {
      title: 'Monthly Budget Planner',
      subtitle: 'Set safe spending limits for each category to protect your savings',
    },
    goals: {
      title: 'Savings Targets',
      subtitle: 'Track progress towards your savings goals step-by-step',
    },
    chat: {
      title: 'AI Money Helper',
      subtitle: 'Ask simple questions about your money and get instant, honest answers',
    },
  };

  const current = titles[activeTab] || titles.dashboard;

  return (
    <header className="h-20 bg-navy-900/60 backdrop-blur-md border-b border-slate-800 px-6 sm:px-8 flex items-center justify-between shrink-0 sticky top-0 z-20">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">{current.title}</h2>
        <p className="text-xs text-slate-400 mt-0.5">{current.subtitle}</p>
      </div>

      <div className="flex items-center gap-2.5 sm:gap-3">
        {/* Notice Bell with Alert Badge */}
        <NotificationBell refreshKey={refreshKey} />

        {/* Load ₹30k Demo Profile */}
        <button
          onClick={onSeedDemo}
          disabled={loading}
          title="Load sample ₹30,000 monthly dataset"
          className="flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-teal-500/10 text-teal-300 border border-teal-500/30 hover:bg-teal-500/20 transition-all disabled:opacity-50"
        >
          <Sparkles className="w-3.5 h-3.5 text-teal-400" />
          <span className="hidden md:inline">Sample Demo</span>
        </button>

        {/* Clear All Data */}
        <button
          onClick={onResetDemo}
          disabled={loading}
          title="Clear all records to start fresh with your own expenses"
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 border border-slate-800 hover:border-rose-500/30 transition-all disabled:opacity-50"
        >
          <Trash2 className="w-3.5 h-3.5 text-rose-400" />
          <span className="hidden md:inline">Clear All</span>
        </button>

        {/* Automated Transaction Import Agent */}
        <button
          onClick={onOpenSmartImport}
          title="Import transactions automatically from bank SMS, UPI alerts, or statements"
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/20 transition-all shadow-sm"
        >
          <Bot className="w-3.5 h-3.5 text-emerald-400" />
          <span className="hidden sm:inline">Import Agent</span>
        </button>

        {/* Quick Add Expense / Income */}
        <button
          onClick={onQuickAdd}
          className="flex items-center gap-2 px-3.5 sm:px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-500 text-navy-950 hover:bg-emerald-400 transition-all shadow-md shadow-emerald-500/20 active:scale-95"
        >
          <Plus className="w-4 h-4 stroke-[2.5]" />
          <span>+ Add Entry</span>
        </button>
      </div>
    </header>
  );
}
