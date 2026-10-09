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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalysis();
  }, []);

  const fetchAnalysis = async () => {
    setLoading(true);
    try {
      const [anaData, sumData] = await Promise.all([
        api.getAnalysis(),
        api.getSummary(),
      ]);
      setAnalysis(anaData);
      setSummary(sumData);
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
      {/* Top Banner: Essential vs Discretionary Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Essential Card */}
        <div className="card-glass rounded-2xl p-6 border-l-4 border-l-blue-500 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4" /> Essential Obligations
            </span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
              {analysis.essential_percentage}% of Outflow
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <h3 className="text-3xl font-black text-white">{formatINR(analysis.essential_spending)}</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Non-negotiable living costs (Rent, Groceries, Electricity, Commute, Medicine). These form your bare-minimum survival baseline.
          </p>
        </div>

        {/* Discretionary Card */}
        <div className="card-glass rounded-2xl p-6 border-l-4 border-l-amber-500 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
              <Sliders className="w-4 h-4" /> Discretionary Lifestyle
            </span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
              {analysis.discretionary_percentage}% of Outflow
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <h3 className="text-3xl font-black text-white">{formatINR(analysis.discretionary_spending)}</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Flexible spending (Food delivery, Dining, Shopping, OTT subscriptions). Trimming this category yields immediate monthly cash surplus.
          </p>
        </div>
      </div>

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
