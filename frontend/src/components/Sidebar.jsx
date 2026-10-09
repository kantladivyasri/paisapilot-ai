import React from 'react';
import {
  LayoutDashboard,
  Receipt,
  PieChart,
  Target,
  Bot,
  SlidersHorizontal,
  Compass,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, onOpenSettings, groqConfigured }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'transactions', label: 'Transactions & CSV', icon: Receipt },
    { id: 'analysis', label: 'AI Spending Analysis', icon: PieChart },
    { id: 'budget', label: 'Budget Planner', icon: Compass },
    { id: 'goals', label: 'Savings Goals', icon: Target },
    { id: 'chat', label: 'AI Finance Assistant', icon: Bot, badge: 'AI' },
  ];

  return (
    <aside className="w-64 bg-navy-900 border-r border-slate-800 flex flex-col justify-between shrink-0 select-none">
      <div>
        {/* Brand Header */}
        <div className="p-6 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-navy-950 font-black text-xl">
              ₹
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight flex items-center gap-1.5">
                PaisaPilot <span className="text-emerald-400 font-semibold text-xs px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">AI</span>
              </h1>
              <p className="text-[11px] text-slate-400 font-medium tracking-wide">
                Understand Money. Plan Future.
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-4 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-3 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-sm shadow-emerald-500/10 font-semibold'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Info & Engine Status */}
      <div className="p-4 border-t border-slate-800/80 space-y-3">
        <div className="bg-slate-900/80 rounded-xl p-3 border border-slate-800 text-xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-slate-400 font-medium">AI Engine Status</span>
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>
          <p className="text-slate-300 font-semibold flex items-center gap-1.5 text-[11px]">
            {groqConfigured ? (
              <>
                <Sparkles className="w-3.5 h-3.5 text-teal-400" />
                Groq LLM Active
              </>
            ) : (
              <>
                <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                Rule Engine (Deterministic)
              </>
            )}
          </p>
        </div>

        <button
          onClick={onOpenSettings}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors border border-transparent hover:border-slate-700"
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>API & Engine Settings</span>
        </button>
      </div>
    </aside>
  );
}
