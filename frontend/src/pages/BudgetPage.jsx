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
  Plus,
  Trash2,
  Edit2,
  CreditCard,
  Shield,
  Zap,
  Calendar,
  Phone,
  Smartphone,
  Send,
  CheckCircle2,
  ArrowRight,
  Layers,
} from 'lucide-react';
import { api } from '../services/api';
import { formatINR } from '../utils/formatters';
import CategoryModal from '../components/CategoryModal';
import RecurringExpenseModal from '../components/RecurringExpenseModal';

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

  // Monthly Common Expenses (Bills, EMIs, Insurance)
  const [recurringData, setRecurringData] = useState({
    items: [],
    total_monthly_commitment: 0,
    active_count: 0,
    breakdown_by_type: {},
  });
  const [isRecurringModalOpen, setIsRecurringModalOpen] = useState(false);
  const [editingRecurringItem, setEditingRecurringItem] = useState(null);
  const [alertStatus, setAlertStatus] = useState(null);
  const [dispatchingSms, setDispatchingSms] = useState(false);
  const [smsActionMsg, setSmsActionMsg] = useState(null);

  const currentMonth = new Date().toISOString().slice(0, 7);

  useEffect(() => {
    fetchBudget();
    fetchRecurringAndAlerts();
  }, []);

  const fetchRecurringAndAlerts = async () => {
    try {
      const [recData, aStatus] = await Promise.all([
        api.getRecurringExpenses(),
        api.getAlertStatus(),
      ]);
      if (recData) setRecurringData(recData);
      if (aStatus) setAlertStatus(aStatus);
    } catch (e) {
      console.error('Failed to load recurring expenses or alert status:', e);
    }
  };

  const handleDeleteRecurring = async (id) => {
    if (!window.confirm('Delete this monthly recurring expense?')) return;
    try {
      await api.deleteRecurringExpense(id);
      fetchRecurringAndAlerts();
      fetchBudget();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleLogRecurringTxn = async (id) => {
    try {
      await api.logRecurringTransaction(id);
      setSmsActionMsg('Recorded as current month transaction and checked budget alerts!');
      fetchBudget();
      fetchRecurringAndAlerts();
      setTimeout(() => setSmsActionMsg(null), 5000);
    } catch (err) {
      alert(err.message);
    }
  };

  const handleTriggerSmsCheck = async () => {
    setDispatchingSms(true);
    setSmsActionMsg(null);
    try {
      const res = await api.checkAndNotifyAlerts(true);
      setSmsActionMsg(
        res.alerts_sent > 0
          ? `Dispatched ${res.alerts_sent} SMS warning alert(s) to your mobile number!`
          : res.messages[0] || 'Budget evaluated: No new over-budget warnings detected.'
      );
      fetchRecurringAndAlerts();
    } catch (err) {
      alert(err.message);
    } finally {
      setDispatchingSms(false);
    }
  };

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

      {/* Toast Notice */}
      {smsActionMsg && (
        <div className="p-4 rounded-xl bg-teal-500/15 border border-teal-500/40 text-teal-300 text-xs font-semibold flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-400" />
            <span>{smsActionMsg}</span>
          </div>
          <button onClick={() => setSmsActionMsg(null)} className="text-teal-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {/* Critical Over-Budget Warning & Mobile SMS Notification Banner */}
      {alertStatus && alertStatus.is_over_budget && (
        <div className="p-5 rounded-2xl bg-rose-500/10 border border-rose-500/30 space-y-3 animate-in fade-in">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2.5 text-rose-400 font-bold text-sm">
              <ShieldAlert className="w-5 h-5 shrink-0" />
              <span>🚨 Active Budget Overrun Warning ({alertStatus.warning_count} Cap Breach{alertStatus.warning_count > 1 ? 'es' : ''})</span>
            </div>
            {alertStatus.has_phone ? (
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-lg flex items-center gap-1.5">
                  <Smartphone className="w-3.5 h-3.5" />
                  SMS Sent to {alertStatus.phone_number}
                </span>
                <button
                  onClick={handleTriggerSmsCheck}
                  disabled={dispatchingSms}
                  className="px-2.5 py-1 text-[11px] font-semibold rounded-lg bg-rose-500/20 text-rose-300 border border-rose-500/30 hover:bg-rose-500/30 transition-all flex items-center gap-1 disabled:opacity-50"
                >
                  <Send className="w-3 h-3" />
                  <span>{dispatchingSms ? 'Sending SMS...' : 'Resend SMS Alert'}</span>
                </button>
              </div>
            ) : (
              <span className="text-[11px] font-medium text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-lg flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5" />
                No mobile linked — Add phone in Profile to receive SMS alerts!
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
            {alertStatus.warnings.map((w, idx) => (
              <div key={idx} className="p-3 bg-slate-950/70 border border-rose-500/20 rounded-xl text-xs space-y-1">
                <div className="flex items-center justify-between font-semibold text-rose-300">
                  <span>{w.category}</span>
                  <span className="font-mono text-rose-400">+{formatINR(w.excess)} Over Limit</span>
                </div>
                <p className="text-[11px] text-slate-300">{w.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}

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

      {/* Monthly Common Expenses (Bills, EMIs, Insurance) */}
      <div className="bg-navy-900 border border-slate-800 rounded-2xl p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-teal-500/10 text-teal-400">
                <Layers className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-white tracking-tight">
                Monthly Common Expenses & Fixed Commitments
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Add recurring obligations like loan EMIs, insurance premiums, house rent, and utility bills.
            </p>
          </div>

          <button
            onClick={() => {
              setEditingRecurringItem(null);
              setIsRecurringModalOpen(true);
            }}
            className="flex items-center gap-2 px-3.5 py-2 text-xs font-bold rounded-xl bg-emerald-500 hover:bg-emerald-400 text-navy-950 transition-all shadow-md shadow-emerald-500/20 shrink-0 self-start sm:self-auto cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>+ Add Common Expense</span>
          </button>
        </div>

        {/* Summary Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Total Monthly Commitment
            </span>
            <span className="text-2xl font-black text-white font-mono mt-1 block">
              {formatINR(recurringData.total_monthly_commitment)}
            </span>
            <span className="text-[11px] text-slate-400 mt-1 block">
              Fixed recurring outflows each month
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Active Recurring Items
            </span>
            <span className="text-2xl font-black text-teal-400 font-mono mt-1 block">
              {recurringData.active_count}
            </span>
            <span className="text-[11px] text-slate-400 mt-1 block">
              Bills, EMIs & Insurance policies
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Commitment vs Income
            </span>
            <span className="text-2xl font-black text-emerald-400 font-mono mt-1 block">
              {incomeNum > 0
                ? `${Math.round((recurringData.total_monthly_commitment / incomeNum) * 100)}%`
                : '0%'}
            </span>
            <span className="text-[11px] text-slate-400 mt-1 block">
              Of your monthly take-home income
            </span>
          </div>
        </div>

        {/* Recurring Items List / Grid */}
        {recurringData.items && recurringData.items.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {recurringData.items.map((item) => {
              const typeBadgeColors = {
                emi: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
                insurance: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
                bill: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
                subscription: 'bg-teal-500/15 text-teal-300 border-teal-500/30',
                rent: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
                other: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
              };
              const badgeClass = typeBadgeColors[item.expense_type] || typeBadgeColors.other;

              return (
                <div
                  key={item.id}
                  className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition-all space-y-3 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${badgeClass}`}>
                        {item.expense_type}
                      </span>
                      <span className="text-[11px] text-slate-400 font-medium flex items-center gap-1">
                        <Calendar className="w-3 h-3 text-emerald-400" />
                        Due on {item.due_day}th
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-white mt-2 truncate">
                      {item.title}
                    </h4>
                    <p className="text-xs text-slate-400 mt-0.5 truncate">
                      {item.category} • {item.payment_method}
                    </p>
                    {item.notes && (
                      <p className="text-[11px] text-slate-500 mt-1 italic truncate">
                        {item.notes}
                      </p>
                    )}
                  </div>

                  <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-base font-black text-emerald-400 font-mono">
                      {formatINR(item.amount)}
                      <span className="text-[10px] text-slate-400 font-normal">/mo</span>
                    </span>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleLogRecurringTxn(item.id)}
                        title="Log this bill/EMI as transaction for this month"
                        className="px-2 py-1 text-[11px] font-semibold rounded-lg bg-teal-500/10 text-teal-300 border border-teal-500/30 hover:bg-teal-500/20 transition-all flex items-center gap-1 cursor-pointer"
                      >
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Log Paid</span>
                      </button>
                      <button
                        onClick={() => {
                          setEditingRecurringItem(item);
                          setIsRecurringModalOpen(true);
                        }}
                        className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeleteRecurring(item.id)}
                        className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-8 rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-center space-y-2">
            <Layers className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs text-slate-400">
              No common monthly expenses added yet.
            </p>
            <button
              onClick={() => {
                setEditingRecurringItem(null);
                setIsRecurringModalOpen(true);
              }}
              className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold underline cursor-pointer"
            >
              Add your first EMI, Bill, or Insurance policy
            </button>
          </div>
        )}
      </div>

      <RecurringExpenseModal
        isOpen={isRecurringModalOpen}
        onClose={() => {
          setIsRecurringModalOpen(false);
          setEditingRecurringItem(null);
        }}
        onSaved={fetchRecurringAndAlerts}
        item={editingRecurringItem}
      />

      <CategoryModal
        isOpen={isCategoryModalOpen}
        onClose={() => setIsCategoryModalOpen(false)}
        onCategoriesUpdated={fetchBudget}
      />
    </div>
  );
}
