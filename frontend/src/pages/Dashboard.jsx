import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  PiggyBank,
  AlertTriangle,
  Sparkles,
  ArrowRight,
  PlusCircle,
  FileSpreadsheet,
  Calendar,
  Tags,
  Bell,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import StatCard from '../components/StatCard';
import SalaryModal from '../components/SalaryModal';
import CategoryModal from '../components/CategoryModal';
import { api } from '../services/api';
import { formatINR, formatDate, getCategoryColor } from '../utils/formatters';

const PERIOD_OPTIONS = [
  { id: 'daily', label: 'Today' },
  { id: 'weekly', label: 'This Week' },
  { id: 'monthly', label: 'This Month' },
  { id: 'yearly', label: 'This Year' },
  { id: 'custom', label: 'Custom' },
];

export default function Dashboard({ onNavigate, onQuickAdd, onOpenImport }) {
  const [periodType, setPeriodType] = useState('monthly');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const [periodReport, setPeriodReport] = useState(null);
  const [salaryData, setSalaryData] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [recentTxns, setRecentTxns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showWarningDetails, setShowWarningDetails] = useState(false);

  // Modals
  const [isSalaryModalOpen, setIsSalaryModalOpen] = useState(false);
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);

  const currentMonthStr = new Date().toISOString().slice(0, 7);

  useEffect(() => {
    fetchDashboardData();
  }, [periodType, customStart, customEnd]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const params = {};
      if (periodType === 'custom') {
        if (customStart) params.start_date = customStart;
        if (customEnd) params.end_date = customEnd;
      }

      const [reportData, salData, anaData, txnData, fcData] = await Promise.all([
        api.getPeriodReport(periodType, params),
        api.getSalary(currentMonthStr),
        api.getAnalysis(currentMonthStr),
        api.getTransactions({ page: 1, page_size: 5 }),
        api.getForecast(currentMonthStr),
      ]);

      setPeriodReport(reportData);
      setSalaryData(salData);
      setAnalysis(anaData);
      setForecast(fcData);
      const items = txnData?.items ? txnData.items : Array.isArray(txnData) ? txnData.slice(0, 5) : [];
      setRecentTxns(items);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSalarySaved = (updatedSalary) => {
    setSalaryData(updatedSalary);
    fetchDashboardData();
  };

  const handleCategoriesUpdated = () => {
    fetchDashboardData();
  };

  if (loading && !periodReport) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-emerald-500/20 border-t-emerald-400 rounded-full animate-spin"></div>
          <span className="text-xs text-slate-400 font-medium tracking-wide">
            Loading your money details...
          </span>
        </div>
      </div>
    );
  }

  const currentP = periodReport?.current_period;
  const previousP = periodReport?.previous_period;
  const comparison = periodReport?.comparison;
  const hasData = currentP && currentP.transaction_count > 0;

  // Donut chart data
  const pieData = (currentP?.category_breakdown || []).map((c) => ({
    name: c.category,
    value: c.amount,
    percentage: c.percentage,
    color: c.color || getCategoryColor(c.category),
  }));

  // Trend data from real period points
  const trendData = currentP?.trend_data || [];

  return (
    <div className="p-6 sm:p-8 space-y-6 sm:space-y-8 max-w-7xl mx-auto">
      {/* Top Controls: Friendly Period Switcher & Setup Buttons */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <span>Money Overview</span>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Live Data
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {currentP?.period_label || 'Current Period'} ({currentP?.start_date} to {currentP?.end_date})
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Period View Switcher */}
          <div className="flex items-center p-1 bg-slate-950 rounded-xl border border-slate-800 text-xs">
            {PERIOD_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                onClick={() => setPeriodType(opt.id)}
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  periodType === opt.id
                    ? 'bg-emerald-500 text-navy-950 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Manage Categories Trigger */}
          <button
            type="button"
            onClick={() => setIsCategoryModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-600 transition-colors shadow-sm"
          >
            <Tags className="w-3.5 h-3.5 text-teal-400" />
            <span>Categories</span>
          </button>

          {/* Set Salary Trigger */}
          <button
            type="button"
            onClick={() => setIsSalaryModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-navy-950 hover:opacity-90 transition-opacity shadow-sm"
          >
            <Wallet className="w-3.5 h-3.5" />
            <span>{salaryData?.current_month_salary > 0 ? 'Edit Salary' : 'Set Salary'}</span>
          </button>
        </div>
      </div>

      {/* Custom Date Range Picker when Custom tab is selected */}
      {periodType === 'custom' && (
        <div className="flex flex-wrap items-center gap-3 p-4 rounded-xl bg-slate-950/70 border border-slate-800 animate-in fade-in duration-200">
          <Calendar className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="text-xs font-semibold text-slate-300">Choose custom dates:</span>
          <div className="flex items-center gap-2 text-xs">
            <input
              type="date"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              className="bg-navy-900 border border-slate-800 rounded-lg px-2.5 py-1 text-white focus:outline-none focus:border-emerald-500"
            />
            <span className="text-slate-500 font-medium">to</span>
            <input
              type="date"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="bg-navy-900 border border-slate-800 rounded-lg px-2.5 py-1 text-white focus:outline-none focus:border-emerald-500"
            />
          </div>
          <button
            type="button"
            onClick={fetchDashboardData}
            className="px-3 py-1 text-xs font-bold rounded-lg bg-emerald-500 text-navy-950 hover:bg-emerald-400"
          >
            Show
          </button>
        </div>
      )}

      {/* Simple "Your Money This Month" Salary Card */}
      <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-br from-navy-900 via-navy-900 to-slate-900 border border-slate-800 shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-teal-400 uppercase tracking-wider">
                💵 Your Money This Month
              </span>
              {salaryData?.current_month_salary > 0 ? (
                <button
                  type="button"
                  onClick={() => setIsSalaryModalOpen(true)}
                  className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold hover:bg-emerald-500/20 cursor-pointer transition-colors"
                  title="Click to update salary"
                >
                  Active • Click to Edit ✍️
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setIsSalaryModalOpen(true)}
                  className="text-[10px] px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold hover:bg-amber-500/30 transition-colors cursor-pointer animate-pulse"
                  title="Click to enter your monthly salary"
                >
                  Salary Not Set • Click to Enter ✍️
                </button>
              )}
            </div>
            <p className="text-xs text-slate-400">
              Money In (Salary) minus Money Spent = Money Left in your pocket
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 lg:gap-4">
            {/* Money In */}
            <div
              onClick={() => setIsSalaryModalOpen(true)}
              title="Click to enter or update your monthly salary"
              className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900 cursor-pointer transition-all group select-none"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">🟢 Money In</span>
                <span className="text-[9px] text-emerald-400 font-semibold opacity-75 group-hover:opacity-100 group-hover:underline">Edit ✍️</span>
              </div>
              <span className="text-lg font-black text-emerald-400 block mt-0.5">
                {salaryData?.current_month_salary > 0
                  ? formatINR(salaryData.current_month_salary)
                  : '₹0'}
              </span>
              <span className="text-[10px] text-slate-500">Monthly Salary</span>
            </div>

            {/* Money Spent */}
            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">🔴 Money Spent</span>
              <span className="text-lg font-black text-rose-400 block mt-0.5">
                {formatINR(salaryData?.total_expenses || 0)}
              </span>
              <span className="text-[10px] text-slate-500">This Month</span>
            </div>

            {/* Money Left */}
            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">💰 Money Left</span>
              <span
                className={`text-lg font-black block mt-0.5 ${
                  (salaryData?.remaining_balance || 0) >= 0 ? 'text-teal-300' : 'text-rose-400'
                }`}
              >
                {formatINR(salaryData?.remaining_balance || 0)}
              </span>
              <span className="text-[10px] text-slate-500">
                {(salaryData?.remaining_balance || 0) >= 0 ? 'Safe to Spend' : 'In Deficit'}
              </span>
            </div>

            {/* Savings Habit */}
            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">⭐ Saved</span>
              <span
                className={`text-lg font-black block mt-0.5 ${
                  (salaryData?.savings_rate || 0) >= 20 ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                {salaryData?.savings_rate || 0}%
              </span>
              <span className="text-[10px] text-slate-500">
                {(salaryData?.savings_rate || 0) >= 20 ? 'Great Habit!' : 'Can improve'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Clean Month-End Forecast Card (Alerts consolidated to top Notice Bell) */}
      {forecast && (
        <div className="card-glass rounded-2xl p-5 sm:p-6 space-y-4 border border-slate-800 shadow-xl bg-gradient-to-br from-navy-900/90 via-slate-900/90 to-navy-950">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white">Month-End Money Forecast</h3>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
                    Day {forecast.days_passed} of {forecast.total_days}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  How much you are likely to spend and save by the end of this month
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`text-xs font-bold px-3 py-1 rounded-full border ${
                  forecast.projected_status === 'healthy'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : forecast.projected_status === 'caution'
                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                    : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                }`}
              >
                {forecast.projected_status === 'healthy'
                  ? 'On Track 👍'
                  : forecast.projected_status === 'caution'
                  ? 'Caution: Spending Faster'
                  : 'Deficit Risk 🔴'}
              </span>
            </div>
          </div>

          {/* 4 Clean Metric Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-0.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Expected Total Spending</span>
              <span className="text-base sm:text-lg font-black text-white block">
                {formatINR(forecast.projected_expenses)}
              </span>
              <span className="text-[11px] text-slate-400 block">
                Already spent: <b className="text-slate-300">{formatINR(forecast.current_expenses)}</b>
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-0.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Expected Savings at Month-End</span>
              <span
                className={`text-base sm:text-lg font-black block ${
                  forecast.projected_savings >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {formatINR(forecast.projected_savings)}
              </span>
              <span className="text-[11px] text-slate-400 block">
                Estimated rate: <b className="text-teal-400">{forecast.projected_savings_rate}%</b>
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-0.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Daily Spending Speed</span>
              <span className="text-base sm:text-lg font-black text-teal-300 block">
                {formatINR(forecast.daily_spending_pace)} / day
              </span>
              <span className="text-[11px] text-slate-400 block">
                Normal speed: <b className="text-slate-300">{formatINR(forecast.regular_daily_baseline)}/day</b>
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-0.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Shopping & Fun Spending</span>
              <span
                className={`text-base sm:text-lg font-black block ${
                  forecast.is_overspending_on_unwanted ? 'text-amber-400' : 'text-slate-200'
                }`}
              >
                {formatINR(forecast.total_unwanted_spent)}
              </span>
              <span className="text-[11px] text-slate-400 block">
                Expected: <b className="text-slate-300">{formatINR(forecast.projected_unwanted_spent)}</b>
              </span>
            </div>
          </div>

          {/* Simple, Non-Intrusive Notice Pointer (Directs user to top Notice Bell) */}
          {forecast.is_overspending_on_unwanted && (
            <div className="pt-2">
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2 text-amber-300">
                  <Bell className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>
                    <b>Notice:</b> You have spending alerts. Tap the <b>Bell icon</b> at the top anytime to view details and advice.
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowWarningDetails(!showWarningDetails)}
                  className="text-xs text-amber-300 hover:text-white font-semibold flex items-center gap-1 self-start sm:self-auto"
                >
                  <span>{showWarningDetails ? 'Hide Details' : 'View Details'}</span>
                  {showWarningDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
              </div>

              {/* Optional Collapsible Detail List if user explicitly clicks */}
              {showWarningDetails && forecast.unwanted_spending_alerts && (
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2.5 animate-in fade-in duration-150">
                  {forecast.unwanted_spending_alerts.map((alert, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-slate-950/90 border border-amber-500/30 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between font-bold text-white">
                        <span>{alert.category}</span>
                        <span className="text-[10px] text-amber-300 bg-amber-500/20 px-2 py-0.5 rounded-full">
                          +{alert.excess_percentage}% high
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-300">
                        Spent {formatINR(alert.current_spent)}. Normal benchmark is {formatINR(alert.regular_baseline)}.
                      </p>
                      <p className="text-[11px] text-teal-300 font-medium">
                        💡 {alert.recommendation}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 4 Friendly KPI Cards for the chosen period */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Money In"
          amount={currentP?.total_income || 0}
          subtitle={`Previous: ${formatINR(comparison?.previous_income || 0)}`}
          icon={TrendingUp}
          badgeText="Inflow"
          badgeType="positive"
        />
        <StatCard
          title="Total Money Out"
          amount={currentP?.total_expenses || 0}
          subtitle={`${currentP?.transaction_count || 0} entries`}
          icon={TrendingDown}
          badgeText={
            comparison?.expense_change_amount > 0
              ? `+${comparison.expense_change_percent}% vs Prior`
              : comparison?.expense_change_amount < 0
              ? `${comparison.expense_change_percent}% vs Prior`
              : 'Same as Prior'
          }
          badgeType={comparison?.expense_change_amount > 0 ? 'negative' : 'positive'}
        />
        <StatCard
          title="Net Balance Left"
          amount={currentP?.remaining_balance || 0}
          subtitle="Money In minus Money Out"
          icon={Wallet}
          badgeText={currentP?.remaining_balance >= 0 ? 'Surplus' : 'Deficit'}
          badgeType={currentP?.remaining_balance >= 0 ? 'positive' : 'negative'}
        />
        <StatCard
          title="Savings Habit"
          amount={currentP?.savings_rate || 0}
          isCurrency={false}
          rawSuffix="%"
          subtitle={`Previous rate: ${previousP?.savings_rate || 0}%`}
          icon={PiggyBank}
          badgeText={currentP?.savings_rate >= 20 ? 'Great' : 'Try to Save'}
          badgeType={currentP?.savings_rate >= 20 ? 'positive' : 'warning'}
        />
      </div>

      {!hasData ? (
        /* Friendly Empty State */
        <div className="card-glass rounded-3xl p-10 sm:p-12 text-center max-w-xl mx-auto space-y-4 border border-dashed border-slate-700">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center mx-auto border border-emerald-500/20">
            <Sparkles className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-base sm:text-lg font-bold text-white">No Expenses in This Period</h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              No entries found for {periodType} ({currentP?.start_date} to {currentP?.end_date}).
              Add an expense or tap "Sample Demo" at the top to see how Nidhi Pilot works!
            </p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <button
              onClick={onQuickAdd}
              className="px-4 py-2 text-xs font-bold rounded-xl bg-emerald-500 text-navy-950 hover:bg-emerald-400 transition-all flex items-center gap-2"
            >
              <PlusCircle className="w-4 h-4" />
              <span>+ Add Entry</span>
            </button>
            <button
              onClick={onOpenImport}
              className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-800 text-slate-200 hover:bg-slate-700 transition-all flex items-center gap-2 border border-slate-700"
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>Import Bank File</span>
            </button>
          </div>
        </div>
      ) : (
        /* Rich Data View */
        <>
          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Donut Chart: Where Did My Money Go? */}
            <div className="card-glass rounded-2xl p-5 sm:p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-sm font-bold text-white">Where Did My Money Go?</h3>
                  <button
                    onClick={() => onNavigate('analysis')}
                    className="text-xs text-emerald-400 hover:underline flex items-center gap-1 font-semibold"
                  >
                    Details <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
                <p className="text-xs text-slate-400 mb-3">
                  Spending split by category in {currentP?.period_label}
                </p>
              </div>

              {pieData.length > 0 ? (
                <div className="h-52 relative flex items-center justify-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        innerRadius={50}
                        outerRadius={75}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(val) => [formatINR(val), 'Spent']}
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          borderColor: '#334155',
                          borderRadius: '12px',
                          fontSize: '12px',
                          color: '#f8fafc',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-[10px] uppercase font-bold text-slate-500">Total Spent</span>
                    <span className="text-sm font-black text-white">
                      {formatINR(currentP.total_expenses, false)}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="h-52 flex items-center justify-center text-xs text-slate-500">
                  No expenses recorded yet.
                </div>
              )}

              {/* Category Mini Legend */}
              <div className="grid grid-cols-2 gap-2 pt-3 border-t border-slate-800">
                {pieData.slice(0, 4).map((c) => (
                  <div key={c.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 truncate">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: c.color }}></span>
                      <span className="text-slate-300 truncate text-[11px] font-medium">{c.name}</span>
                    </div>
                    <span className="text-slate-400 text-[11px] font-semibold">{c.percentage}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Area Chart: Money Flow Over Time */}
            <div className="card-glass rounded-2xl p-5 sm:p-6 lg:col-span-2 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-sm font-bold text-white">
                    {periodType === 'daily'
                      ? 'Today Money Movement'
                      : periodType === 'weekly'
                      ? 'This Week Daily Trend'
                      : periodType === 'yearly'
                      ? 'Annual Monthly Trend'
                      : 'Daily Spending Trend'}
                  </h3>
                  <span className="text-[11px] text-slate-400 font-medium px-2 py-0.5 rounded-md bg-slate-800/80 border border-slate-700/50">
                    Live Record
                  </span>
                </div>
                <p className="text-xs text-slate-400 mb-3">
                  Green shows money coming in, red shows money spent
                </p>
              </div>

              <div className="h-56 sm:h-64 w-full">
                {trendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                      <defs>
                        <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                      <XAxis dataKey="label" stroke="#64748b" fontSize={11} tickLine={false} />
                      <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(val) => `₹${val >= 1000 ? Math.round(val/1000) + 'k' : val}`} />
                      <Tooltip
                        formatter={(val, name) => [formatINR(val), name === 'income' ? 'Income' : 'Expenses']}
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          borderColor: '#334155',
                          borderRadius: '12px',
                          fontSize: '12px',
                          color: '#f8fafc',
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="income"
                        stroke="#10b981"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#incomeGrad)"
                        name="Income"
                      />
                      <Area
                        type="monotone"
                        dataKey="expenses"
                        stroke="#f43f5e"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#expenseGrad)"
                        name="Expenses"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-slate-500">
                    No trend points available for this period.
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-6 pt-3 border-t border-slate-800 text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-1 bg-emerald-400 rounded-full"></span>
                  <span className="text-slate-400 text-[11px]">Money In</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-1 bg-rose-400 rounded-full"></span>
                  <span className="text-slate-400 text-[11px]">Money Spent</span>
                </div>
              </div>
            </div>
          </div>

          {/* Lower Grid: Recent Transactions & AI Money Tips */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Recent Transactions Table */}
            <div className="card-glass rounded-2xl p-5 sm:p-6 lg:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-sm font-bold text-white">Recent Transactions</h3>
                  <p className="text-xs text-slate-400">Your latest money entries</p>
                </div>
                <button
                  onClick={() => onNavigate('transactions')}
                  className="text-xs text-emerald-400 hover:underline flex items-center gap-1 font-semibold"
                >
                  View All <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                      <th className="pb-2.5">Name</th>
                      <th className="pb-2.5">Category</th>
                      <th className="pb-2.5">Method</th>
                      <th className="pb-2.5">Date</th>
                      <th className="pb-2.5 text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-medium">
                    {recentTxns.map((t) => (
                      <tr key={t.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-2.5 text-slate-200 flex items-center gap-2">
                          <span
                            className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                              t.transaction_type === 'income' ? 'bg-emerald-400' : 'bg-rose-400'
                            }`}
                          ></span>
                          <span className="font-semibold truncate max-w-[170px]">{t.description}</span>
                        </td>
                        <td className="py-2.5">
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700/60">
                            {t.category}
                          </span>
                        </td>
                        <td className="py-2.5">
                          <span className="text-[10px] text-slate-400 font-mono">
                            {t.payment_method || 'UPI'}
                          </span>
                        </td>
                        <td className="py-2.5 text-slate-400 text-[11px]">{formatDate(t.date)}</td>
                        <td
                          className={`py-2.5 text-right font-bold ${
                            t.transaction_type === 'income' ? 'text-emerald-400' : 'text-slate-100'
                          }`}
                        >
                          {t.transaction_type === 'income' ? '+' : '-'}
                          {formatINR(t.amount)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* AI Assistant Quick Insights Card */}
            <div className="card-glass rounded-2xl p-5 sm:p-6 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-emerald-400">
                  <Sparkles className="w-4 h-4" />
                  <h3 className="text-sm font-bold text-white">Smart Money Tips</h3>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Based on your ₹{currentP.total_expenses.toLocaleString('en-IN')} spending in {currentP.period_label}:
                </p>

                {analysis?.recommendations && analysis.recommendations.length > 0 ? (
                  <div className="space-y-2 pt-1">
                    {analysis.recommendations.slice(0, 2).map((rec, i) => (
                      <div
                        key={i}
                        className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs space-y-1"
                      >
                        <span className="text-[10px] font-bold text-teal-400 uppercase tracking-wide">
                          {rec.title}
                        </span>
                        <p className="text-slate-300 text-[11px] leading-snug">{rec.action}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-400">
                    Your spending is balanced with a healthy savings buffer.
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-slate-800">
                <button
                  onClick={() => onNavigate('chat')}
                  className="w-full py-2.5 px-4 text-xs font-bold rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-navy-950 hover:opacity-90 transition-opacity flex items-center justify-center gap-2 shadow-md shadow-emerald-500/20"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Ask AI Money Helper</span>
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Salary Modal */}
      <SalaryModal
        isOpen={isSalaryModalOpen}
        onClose={() => setIsSalaryModalOpen(false)}
        currentMonth={currentMonthStr}
        existingSalary={salaryData?.current_month_salary}
        totalExpenses={salaryData?.total_expenses || 0}
        onSalarySaved={handleSalarySaved}
      />

      {/* Category Modal */}
      <CategoryModal
        isOpen={isCategoryModalOpen}
        onClose={() => setIsCategoryModalOpen(false)}
        onCategoriesUpdated={handleCategoriesUpdated}
      />
    </div>
  );
}
