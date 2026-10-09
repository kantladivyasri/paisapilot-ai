import React, { useState, useEffect } from 'react';
import {
  Compass,
  Sparkles,
  AlertOctagon,
  CheckCircle,
  HelpCircle,
  BarChart2,
  TrendingDown,
  ShieldAlert,
  Percent,
  ShieldCheck,
  Tags,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../services/api';
import { formatINR } from '../utils/formatters';
import CategoryModal from '../components/CategoryModal';

export default function BudgetPage() {
  const [budget, setBudget] = useState(null);
  const [monthlyIncome, setMonthlyIncome] = useState('30000');
  const [fixedEssentials, setFixedEssentials] = useState('9500');
  const [variableEssentials, setVariableEssentials] = useState('2500');
  const [obligations, setObligations] = useState('3000');
  const [savingsTarget, setSavingsTarget] = useState('8000');
  const [emergencyTarget, setEmergencyTarget] = useState('2000');
  const [categoryLimits, setCategoryLimits] = useState({});
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  const currentMonth = new Date().toISOString().slice(0, 7);

  useEffect(() => {
    fetchBudget();
  }, []);

  const fetchBudget = async () => {
    setLoading(true);
    try {
      const [data, salData, catsData] = await Promise.all([
        api.getBudget(currentMonth),
        api.getSalary(currentMonth),
        api.getCategories(currentMonth),
      ]);

      if (data) {
        setBudget(data);
        setMonthlyIncome(String(data.monthly_income));
        setFixedEssentials(String(data.essential_expenses));
        setSavingsTarget(String(data.savings_target));
        setEmergencyTarget(String(data.emergency_fund_target || 0));
        setCategoryLimits(data.category_limits || {});
      } else {
        if (salData && salData.current_month_salary > 0) {
          setMonthlyIncome(String(salData.current_month_salary));
        }
        const initialLimits = {};
        (catsData || []).forEach((c) => {
          if (c.budget_limit) initialLimits[c.name] = c.budget_limit;
        });
        setCategoryLimits(initialLimits);
      }
    } catch (err) {
      console.error('Failed to load budget:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateBudget = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage('');

    const incomeVal = parseFloat(monthlyIncome) || 0;
    const totalEssentials =
      (parseFloat(fixedEssentials) || 0) +
      (parseFloat(variableEssentials) || 0) +
      (parseFloat(obligations) || 0);
    const savingsVal = parseFloat(savingsTarget) || 0;
    const emgVal = parseFloat(emergencyTarget) || 0;

    const payload = {
      month: currentMonth,
      monthly_income: incomeVal,
      essential_expenses: totalEssentials,
      savings_target: savingsVal,
      emergency_fund_target: emgVal,
      category_limits: categoryLimits,
    };

    try {
      const saved = await api.saveBudget(payload);
      setBudget(saved);
      setMessage('Budget successfully recalculated and balanced!');
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleLimitChange = (catName, val) => {
    const num = parseFloat(val) || 0;
    setCategoryLimits((prev) => ({
      ...prev,
      [catName]: num,
    }));
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-emerald-500/20 border-t-emerald-400 rounded-full animate-spin"></div>
          <span className="text-xs text-slate-400 font-medium">Loading budget plan...</span>
        </div>
      </div>
    );
  }

  const incomeNum = budget?.monthly_income || parseFloat(monthlyIncome) || 30000;
  const essentialsNum = budget?.essential_expenses || 15000;
  const savingsNum = budget?.savings_target || 8000;
  const emergencyNum = budget?.emergency_fund_target || parseFloat(emergencyTarget) || 0;
  const discretionaryNum =
    budget?.discretionary_allowance ||
    Math.max(0, incomeNum - essentialsNum - savingsNum - emergencyNum);

  // Benchmarks
  const bench50 = incomeNum * 0.5;
  const bench30 = incomeNum * 0.3;
  const bench20 = incomeNum * 0.2;

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-black text-white tracking-tight">Smart Budget Planner</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Personalized needs, wants, emergency funds, and individual category spending caps
          </p>
        </div>
        <button
          onClick={() => setIsCategoryModalOpen(true)}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl bg-slate-900 border border-slate-700 text-slate-300 hover:text-white transition-colors"
        >
          <Tags className="w-3.5 h-3.5 text-teal-400" />
          <span>Category Settings</span>
        </button>
      </div>

      {/* Shortfall Alert if Deficit */}
      {budget && !budget.is_balanced && (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/30 space-y-4">
          <div className="flex items-center gap-3 text-rose-400 font-bold text-base">
            <AlertOctagon className="w-6 h-6 shrink-0" />
            <span>Budget Deficit Warning: Shortfall of {formatINR(budget.deficit_amount)}</span>
          </div>
          <p className="text-xs text-rose-200/90 leading-relaxed font-medium">
            {budget.deficit_warning}
          </p>

          {budget.recovery_plan && (
            <div className="bg-slate-950/80 p-4 rounded-xl border border-rose-500/20 space-y-2 text-xs">
              <span className="font-bold text-rose-300 block uppercase tracking-wider text-[11px]">
                Deficit Recovery & Restructuring Plan:
              </span>
              <ul className="space-y-1.5 text-slate-300 text-[11px]">
                {budget.recovery_plan.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-rose-400 font-bold shrink-0">•</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Main Budget Planner Form & Allocated Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Planner Inputs Form */}
        <div className="card-glass rounded-2xl p-6 space-y-5">
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-emerald-400" />
            <h3 className="text-base font-bold text-white">Monthly Circumstances</h3>
          </div>
          <p className="text-xs text-slate-400">
            Specify your actual income, committed obligations, emergency fund targets, and desired savings.
          </p>

          <form onSubmit={handleGenerateBudget} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Monthly Net Salary / Income (₹)
              </label>
              <input
                type="number"
                min="0"
                step="100"
                required
                value={monthlyIncome}
                onChange={(e) => setMonthlyIncome(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Fixed Essentials (Rent, Utilities, Healthcare)
              </label>
              <input
                type="number"
                min="0"
                step="100"
                value={fixedEssentials}
                onChange={(e) => setFixedEssentials(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Variable Essentials (Groceries, Commute, Fuel)
              </label>
              <input
                type="number"
                min="0"
                step="100"
                value={variableEssentials}
                onChange={(e) => setVariableEssentials(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Committed Obligations (Education EMIs, Loans)
              </label>
              <input
                type="number"
                min="0"
                step="100"
                value={obligations}
                onChange={(e) => setObligations(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Emergency Fund Allocation (₹)
              </label>
              <input
                type="number"
                min="0"
                step="100"
                value={emergencyTarget}
                onChange={(e) => setEmergencyTarget(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Desired Savings Target (₹)
              </label>
              <input
                type="number"
                min="0"
                step="100"
                value={savingsTarget}
                onChange={(e) => setSavingsTarget(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <button
              type="submit"
              disabled={saving}
              className="w-full py-2.5 px-4 text-xs font-bold rounded-xl bg-emerald-500 text-navy-950 hover:bg-emerald-400 transition-all shadow-md shadow-emerald-500/20 disabled:opacity-50"
            >
              {saving ? 'Calculating...' : 'Recalculate & Balance Budget'}
            </button>
          </form>

          {message && (
            <p className="text-xs text-center font-medium text-emerald-400 pt-1">{message}</p>
          )}
        </div>

        {/* Budget Allocation Summary Cards */}
        <div className="lg:col-span-2 space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {/* Essentials Allocation */}
            <div className="card-glass rounded-2xl p-4 border-l-4 border-l-blue-500 space-y-1">
              <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wider block">
                Needs / Essentials
              </span>
              <h4 className="text-xl font-black text-white">{formatINR(essentialsNum)}</h4>
              <p className="text-[10px] text-slate-400">
                {incomeNum > 0 ? ((essentialsNum / incomeNum) * 100).toFixed(1) : 0}% of income
              </p>
            </div>

            {/* Discretionary Allowance */}
            <div className="card-glass rounded-2xl p-4 border-l-4 border-l-amber-500 space-y-1">
              <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider block">
                Wants / Discretionary
              </span>
              <h4 className="text-xl font-black text-white">{formatINR(discretionaryNum)}</h4>
              <p className="text-[10px] text-slate-400">
                {incomeNum > 0 ? ((discretionaryNum / incomeNum) * 100).toFixed(1) : 0}% cap
              </p>
            </div>

            {/* Emergency Fund */}
            <div className="card-glass rounded-2xl p-4 border-l-4 border-l-teal-500 space-y-1">
              <span className="text-[10px] font-bold text-teal-400 uppercase tracking-wider block">
                Emergency Buffer
              </span>
              <h4 className="text-xl font-black text-white">{formatINR(emergencyNum)}</h4>
              <p className="text-[10px] text-slate-400">
                {incomeNum > 0 ? ((emergencyNum / incomeNum) * 100).toFixed(1) : 0}% safety net
              </p>
            </div>

            {/* Proposed Savings */}
            <div className="card-glass rounded-2xl p-4 border-l-4 border-l-emerald-500 space-y-1">
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block">
                Proposed Savings
              </span>
              <h4 className="text-xl font-black text-white">{formatINR(savingsNum)}</h4>
              <p className="text-[10px] text-slate-400">
                {incomeNum > 0 ? ((savingsNum / incomeNum) * 100).toFixed(1) : 0}% target
              </p>
            </div>
          </div>

          {/* 50/30/20 Rule Benchmark Reference */}
          <div className="card-glass rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-1.5">
                  <Percent className="w-4 h-4 text-teal-400" />
                  Needs / Wants / Savings Allocation Breakdown
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Benchmarked against recommended healthy financial ratios
                </p>
              </div>
            </div>

            <div className="space-y-3 pt-2">
              {/* Needs / Essentials */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-semibold">Needs / Essentials (Benchmark ~50%)</span>
                  <span className="text-slate-400">
                    Your Plan: <b>{formatINR(essentialsNum)}</b> (Target: {formatINR(bench50)})
                  </span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-blue-500 h-2.5 rounded-full transition-all"
                    style={{ width: `${Math.min(100, (essentialsNum / incomeNum) * 100)}%` }}
                  ></div>
                </div>
              </div>

              {/* Wants / Discretionary */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-semibold">Wants / Discretionary (Benchmark ~30%)</span>
                  <span className="text-slate-400">
                    Your Plan: <b>{formatINR(discretionaryNum)}</b> (Target: {formatINR(bench30)})
                  </span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-amber-500 h-2.5 rounded-full transition-all"
                    style={{ width: `${Math.min(100, (discretionaryNum / incomeNum) * 100)}%` }}
                  ></div>
                </div>
              </div>

              {/* Savings & Emergency */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-semibold">Savings & Emergency Reserve (Benchmark ~20%)</span>
                  <span className="text-slate-400">
                    Your Plan: <b>{formatINR(savingsNum + emergencyNum)}</b> (Target: {formatINR(bench20)})
                  </span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-2.5 rounded-full transition-all"
                    style={{ width: `${Math.min(100, ((savingsNum + emergencyNum) / incomeNum) * 100)}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>

          {/* Category Limits with Live Utilization & Warnings */}
          {budget?.category_progress && budget.category_progress.length > 0 && (
            <div className="card-glass rounded-2xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-white">Active Category Spending Limits & Status</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Real utilization against your monthly category caps
                  </p>
                </div>
                <span className="text-[10px] text-slate-400">
                  <span className="text-amber-400 font-bold">80%+ Caution</span> • <span className="text-rose-400 font-bold">100%+ Exceeded</span>
                </span>
              </div>

              <div className="space-y-4">
                {budget.category_progress.map((item) => {
                  const isCaution = item.percentage >= 80 && item.percentage <= 100;
                  const isExceeded = item.percentage > 100;
                  return (
                    <div key={item.category} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-200">{item.category}</span>
                          {isExceeded && (
                            <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold">
                              <AlertOctagon className="w-3 h-3" /> Exceeded!
                            </span>
                          )}
                          {isCaution && (
                            <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-bold">
                              <AlertTriangle className="w-3 h-3" /> Approaching Cap
                            </span>
                          )}
                        </div>

                        <span
                          className={`font-mono text-xs font-bold ${
                            isExceeded
                              ? 'text-rose-400'
                              : isCaution
                              ? 'text-amber-400'
                              : 'text-slate-300'
                          }`}
                        >
                          {formatINR(item.spent)} / {formatINR(item.budgeted)} ({item.percentage}%)
                        </span>
                      </div>

                      <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                        <div
                          className={`h-2.5 rounded-full transition-all ${
                            isExceeded
                              ? 'bg-rose-500'
                              : isCaution
                              ? 'bg-amber-400'
                              : 'bg-emerald-400'
                          }`}
                          style={{ width: `${Math.min(100, item.percentage)}%` }}
                        ></div>
                      </div>

                      <div className="flex justify-between items-center text-[10px] text-slate-500 pt-0.5">
                        <span>
                          {item.budgeted - item.spent >= 0
                            ? `Remaining allowance: ${formatINR(item.budgeted - item.spent)}`
                            : `Over limit by: ${formatINR(item.spent - item.budgeted)}`}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      <CategoryModal
        isOpen={isCategoryModalOpen}
        onClose={() => setIsCategoryModalOpen(false)}
        onCategoriesUpdated={fetchBudget}
      />
    </div>
  );
}
