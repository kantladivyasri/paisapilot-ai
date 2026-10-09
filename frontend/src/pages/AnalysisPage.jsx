import React, { useState, useEffect } from 'react';
import {
  PieChart,
  ShieldCheck,
  AlertTriangle,
  Lightbulb,
  ArrowUpRight,
  ArrowDownRight,
  Sliders,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { api } from '../services/api';
import { formatINR, getCategoryColor } from '../utils/formatters';

export default function AnalysisPage() {
  const [analysis, setAnalysis] = useState(null);
  const [summary, setSummary] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalysis();
  }, []);

  const fetchAnalysis = async () => {
    setLoading(true);
    try {
      const [anaData, sumData, foreData] = await Promise.all([
        api.getAnalysis(),
        api.getSummary(),
        api.getForecast(),
      ]);
      setAnalysis(anaData);
      setSummary(sumData);
      setForecast(foreData);
    } catch (err) {
      console.error('Failed to load analysis:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-emerald-500/20 border-t-emerald-400 rounded-full animate-spin"></div>
          <span className="text-xs text-slate-400 font-medium">Crunching spending metrics...</span>
        </div>
      </div>
    );
  }

  if (!analysis || !summary || summary.transaction_count === 0) {
    return (
      <div className="p-8 max-w-xl mx-auto text-center space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-slate-800/80 text-slate-400 flex items-center justify-center mx-auto border border-slate-700">
          <PieChart className="w-8 h-8" />
        </div>
        <h3 className="text-base font-bold text-white">No Expense Analysis Available</h3>
        <p className="text-xs text-slate-400">
          Add or import transactions to reveal category drivers, essential vs discretionary splits, and actionable savings opportunities.
        </p>
      </div>
    );
  }

  const categoryBarData = (analysis.category_breakdown || []).map((c) => ({
    name: c.category,
    amount: c.amount,
    percentage: c.percentage,
    color: getCategoryColor(c.category),
  }));

  const mom = analysis.month_over_month;

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Banner: Needs vs Wants Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Essential Card */}
        <div className="card-glass rounded-2xl p-6 border-l-4 border-l-blue-500 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4" /> 🛡️ Living Essentials (Needs)
            </span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
              {analysis.essential_percentage}% of spending
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <h3 className="text-3xl font-black text-white">{formatINR(analysis.essential_spending)}</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Must-have basic living expenses like groceries, rent, utilities, commute, and medicine.
          </p>
        </div>

        {/* Discretionary Card */}
        <div className="card-glass rounded-2xl p-6 border-l-4 border-l-amber-500 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
              <Sliders className="w-4 h-4" /> 🛍️ Fun & Shopping (Wants)
            </span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
              {analysis.discretionary_percentage}% of spending
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <h3 className="text-3xl font-black text-white">{formatINR(analysis.discretionary_spending)}</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Lifestyle spending like dining out, shopping, and entertainment. Cutting back here saves you money immediately.
          </p>
        </div>
      </div>

      {/* Month-End Money Forecast */}
      {forecast && (
        <div className="card-glass rounded-2xl p-6 space-y-5 border border-slate-800 shadow-xl bg-gradient-to-br from-navy-900/90 via-slate-900/95 to-navy-950">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white">Month-End Spending & Savings Forecast</h3>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                    Day {forecast.days_passed} of {forecast.total_days} ({forecast.days_remaining} days left)
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Predicts your final spending and savings based on how fast you are spending daily
                </p>
              </div>
            </div>

            <span
              className={`text-xs font-bold px-3 py-1 rounded-full border self-start sm:self-auto ${
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

          {/* 4 Forecast KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Expected Total Spending</span>
              <span className="text-xl font-black text-white">{formatINR(forecast.projected_expenses)}</span>
              <span className="text-[11px] text-slate-400 block">
                Spent so far: <b className="text-slate-300">{formatINR(forecast.current_expenses)}</b>
              </span>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Expected Savings</span>
              <span
                className={`text-xl font-black ${
                  forecast.projected_savings >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {formatINR(forecast.projected_savings)}
              </span>
              <span className="text-[11px] text-slate-400 block">
                Estimated rate: <b className="text-teal-400">{forecast.projected_savings_rate}%</b>
              </span>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Daily Spending Speed</span>
              <span className="text-xl font-black text-teal-300">
                {formatINR(forecast.daily_spending_pace)} / day
              </span>
              <span className="text-[11px] text-slate-400 block">
                Normal speed: <b className="text-slate-300">{formatINR(forecast.regular_daily_baseline)}/day</b>
              </span>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Shopping & Fun Spending</span>
              <span className="text-xl font-black text-amber-300">
                {formatINR(forecast.projected_unwanted_spent)}
              </span>
              <span className="text-[11px] text-slate-400 block">
                Normal benchmark: <b className="text-slate-300">{formatINR(forecast.regular_unwanted_baseline)}</b>
              </span>
            </div>
          </div>

          {/* Alert Notice Section */}
          <div className="pt-2 border-t border-slate-800/80 space-y-3">
            {forecast.unwanted_spending_alerts && forecast.unwanted_spending_alerts.length > 0 ? (
              <div className="space-y-3">
                <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                    <span>
                      <b>Notice:</b> {forecast.unwanted_spending_alerts.length} categories have higher than normal spending.
                      Check the <b>Notice Bell</b> at the top anytime for quick alerts.
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {forecast.unwanted_spending_alerts.map((alert, idx) => (
                    <div
                      key={idx}
                      className={`p-4 rounded-xl border text-xs space-y-2 transition-all ${
                        alert.severity === 'critical'
                          ? 'bg-rose-500/10 border-rose-500/30'
                          : 'bg-amber-500/10 border-amber-500/30'
                      }`}
                    >
                      <div className="flex items-center justify-between font-bold">
                        <span className="text-white text-sm">{alert.category}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full uppercase bg-amber-500/20 text-amber-300">
                          +{alert.excess_percentage}% high
                        </span>
                      </div>
                      <p className="text-slate-300 text-xs leading-relaxed">
                        Spent <b>{formatINR(alert.current_spent)}</b> so far. Likely to reach <b>{formatINR(alert.projected_spent)}</b>.
                      </p>
                      <p className="text-emerald-400 font-medium text-[11px] pt-1 border-t border-slate-800/60">
                        💡 {alert.recommendation}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>
                  <b>Spending Under Control:</b> You are not overspending on unwanted items this month. Shopping and entertainment are within normal limits!
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Breakdown Chart */}
      <div className="card-glass rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white">Expense Distribution by Category</h3>
            <p className="text-xs text-slate-400">Ranked from highest outflow to lowest</p>
          </div>
          <span className="text-[11px] font-mono text-slate-400 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800">
            Total Outflow: {formatINR(summary.total_expenses)}
          </span>
        </div>

        <div className="h-72 w-full pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={categoryBarData} layout="vertical" margin={{ top: 0, right: 30, left: 40, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis type="number" stroke="#64748b" fontSize={11} tickFormatter={(val) => `₹${val}`} />
              <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={12} tickLine={false} />
              <Tooltip
                formatter={(val) => [formatINR(val), 'Amount Spent']}
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '12px',
                  fontSize: '12px',
                  color: '#f8fafc',
                }}
              />
              <Bar dataKey="amount" radius={[0, 8, 8, 0]}>
                {categoryBarData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Month-over-Month & Anomalies Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Month over Month */}
        <div className="card-glass rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-white">Month-over-Month Shift</h3>
          </div>

          {mom?.has_sufficient_data ? (
            <div className="grid grid-cols-3 gap-3 pt-2">
              <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase font-bold block">Income Shift</span>
                <span className={`text-sm font-bold flex items-center gap-1 mt-1 ${mom.income_change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {mom.income_change >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                  {formatINR(Math.abs(mom.income_change))}
                </span>
              </div>
              <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase font-bold block">Expense Shift</span>
                <span className={`text-sm font-bold flex items-center gap-1 mt-1 ${mom.expense_change <= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {mom.expense_change > 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                  {formatINR(Math.abs(mom.expense_change))}
                </span>
              </div>
              <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase font-bold block">Savings Rate Shift</span>
                <span className={`text-sm font-bold flex items-center gap-1 mt-1 ${mom.savings_change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {mom.savings_change >= 0 ? '+' : ''}{mom.savings_change}%
                </span>
              </div>
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400 leading-relaxed">
              ℹ️ Current records cover a single active billing cycle (<b>{mom?.current_month}</b>).
              Month-over-month trajectory requires data spanning multiple months. No trend is fabricated.
            </div>
          )}
        </div>

        {/* Unusual Spending / Anomalies */}
        <div className="card-glass rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-bold text-white">High Impact Expenses</h3>
          </div>

          {analysis.anomalies && analysis.anomalies.length > 0 ? (
            <div className="space-y-2">
              {analysis.anomalies.map((anom, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs space-y-1">
                  <div className="flex items-center justify-between font-bold text-amber-300">
                    <span>{anom.description}</span>
                    <span>{formatINR(anom.amount)}</span>
                  </div>
                  <p className="text-amber-200/80 text-[11px]">{anom.reason}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400">
              ✅ No single transaction represents an outsized disproportionate shock to your monthly budget.
            </div>
          )}
        </div>
      </div>

      {/* Actionable Recommendations */}
      <div className="card-glass rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-teal-400" />
          <h3 className="text-sm font-bold text-white">Actionable Financial Opportunities</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(analysis.recommendations || []).map((rec, idx) => (
            <div key={idx} className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-500/20 text-teal-300 border border-teal-500/30">
                  {rec.category}
                </span>
                {rec.potential_savings > 0 && (
                  <span className="text-xs font-mono font-bold text-emerald-400">
                    Save {formatINR(rec.potential_savings)}/mo
                  </span>
                )}
              </div>
              <h4 className="text-xs font-bold text-white">{rec.title}</h4>
              <p className="text-xs text-slate-300 leading-relaxed text-[11px]">{rec.action}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
