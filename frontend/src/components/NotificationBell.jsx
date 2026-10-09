import React, { useState, useEffect, useRef } from 'react';
import { Bell, AlertTriangle, AlertCircle, Lightbulb, CheckCircle2, X } from 'lucide-react';
import { api } from '../services/api';
import { formatINR } from '../utils/formatters';

export default function NotificationBell({ refreshKey }) {
  const [isOpen, setIsOpen] = useState(false);
  const [notices, setNotices] = useState([]);
  const [loading, setLoading] = useState(false);
  const popoverRef = useRef(null);

  useEffect(() => {
    fetchNotices();
  }, [refreshKey]);

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (popoverRef.current && !popoverRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const fetchNotices = async () => {
    try {
      setLoading(true);
      const [forecastData, analysisData, summaryData] = await Promise.allSettled([
        api.getForecast(),
        api.getAnalysis(),
        api.getSummary(),
      ]);

      const items = [];

      // 1. Forecast deficit risk
      if (forecastData.status === 'fulfilled' && forecastData.value) {
        const fc = forecastData.value;
        if (fc.projected_status === 'deficit_risk') {
          items.push({
            id: 'deficit_risk',
            type: 'urgent',
            title: 'High Deficit Risk This Month',
            message: `At your current spending pace, your expenses will exceed your salary by ${formatINR(Math.abs(fc.projected_savings))}.`,
            action: 'Try cutting down on non-essential purchases to stay in safe balance.',
          });
        }

        // Unwanted / discretionary overspending
        if (fc.unwanted_spending_alerts && fc.unwanted_spending_alerts.length > 0) {
          fc.unwanted_spending_alerts.forEach((alert, idx) => {
            items.push({
              id: `unwanted_${idx}`,
              type: alert.severity === 'critical' ? 'urgent' : 'warning',
              title: `High Spending on ${alert.category}`,
              message: `You spent ${formatINR(alert.current_spent)} so far. Estimated month-end is ${formatINR(alert.projected_spent)} (+${alert.excess_percentage}% over baseline).`,
              action: alert.recommendation || `Cut down on ${alert.category.toLowerCase()} to protect your savings.`,
            });
          });
        }
      }

      // 2. Budget overruns from analysis
      if (analysisData.status === 'fulfilled' && analysisData.value) {
        const an = analysisData.value;
        if (an.budget_overruns && an.budget_overruns.length > 0) {
          an.budget_overruns.forEach((bo, idx) => {
            items.push({
              id: `overrun_${idx}`,
              type: 'urgent',
              title: `${bo.category} Over Budget Limit`,
              message: `You spent ${formatINR(bo.spent)}, which is ${formatINR(bo.excess)} over your limit of ${formatINR(bo.limit)}.`,
              action: 'Pause spending in this category for the rest of the month.',
            });
          });
        }

        // Actionable recommendation tips
        if (an.recommendations && an.recommendations.length > 0) {
          an.recommendations.slice(0, 2).forEach((rec, idx) => {
            items.push({
              id: `tip_${idx}`,
              type: 'tip',
              title: `Savings Tip: ${rec.title}`,
              message: rec.action,
              action: rec.potential_savings > 0 ? `Potential monthly savings: ${formatINR(rec.potential_savings)}` : null,
            });
          });
        }
      }

      // 3. Low balance alert from summary
      if (summaryData.status === 'fulfilled' && summaryData.value) {
        const sum = summaryData.value;
        if (sum.current_month_salary > 0 && sum.available_balance < 0) {
          items.push({
            id: 'negative_balance',
            type: 'urgent',
            title: 'Salary Balance Negative',
            message: `You have spent more than your recorded salary by ${formatINR(Math.abs(sum.available_balance))}.`,
            action: 'Avoid further discretionary purchases until next month.',
          });
        }
      }

      setNotices(items);
    } catch (err) {
      console.error('Failed to fetch notices:', err);
    } finally {
      setLoading(false);
    }
  };

  const urgentCount = notices.filter((n) => n.type === 'urgent').length;
  const warningCount = notices.filter((n) => n.type === 'warning').length;
  const totalCount = notices.length;

  return (
    <div className="relative" ref={popoverRef}>
      {/* Bell Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        title="View Alerts & Notices"
        className={`relative p-2.5 rounded-xl border transition-all ${
          isOpen
            ? 'bg-slate-800 text-white border-slate-700 shadow-md'
            : totalCount > 0
            ? 'bg-slate-900/90 text-amber-300 border-amber-500/30 hover:bg-slate-800 hover:text-white'
            : 'bg-slate-900/80 text-slate-400 border-slate-800 hover:bg-slate-800 hover:text-white'
        }`}
      >
        <Bell className="w-4 h-4" />
        {totalCount > 0 && (
          <span
            className={`absolute -top-1 -right-1 px-1.5 py-0.2 min-w-[18px] h-[18px] flex items-center justify-center text-[10px] font-black rounded-full text-white shadow-md animate-pulse ${
              urgentCount > 0
                ? 'bg-rose-500 ring-2 ring-navy-950'
                : 'bg-amber-500 ring-2 ring-navy-950'
            }`}
          >
            {totalCount}
          </span>
        )}
      </button>

      {/* Notices Dropdown Popover */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2">
          {/* Header */}
          <div className="px-4 py-3 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-amber-400" />
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                Notices & Alerts
              </h3>
              {totalCount > 0 && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                  {totalCount} active
                </span>
              )}
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Notice List */}
          <div className="max-h-96 overflow-y-auto p-3 space-y-2.5">
            {notices.length === 0 ? (
              <div className="py-8 text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                <p className="text-xs font-bold text-white">All Good! No Alerts</p>
                <p className="text-[11px] text-slate-400 px-6">
                  Your expenses, salary balance, and budgets are tracking smoothly.
                </p>
              </div>
            ) : (
              notices.map((n) => {
                const isUrgent = n.type === 'urgent';
                const isWarning = n.type === 'warning';
                const isTip = n.type === 'tip';

                return (
                  <div
                    key={n.id}
                    className={`p-3 rounded-xl border text-xs space-y-1.5 transition-all ${
                      isUrgent
                        ? 'bg-rose-500/10 border-rose-500/30'
                        : isWarning
                        ? 'bg-amber-500/10 border-amber-500/30'
                        : 'bg-teal-500/10 border-teal-500/20'
                    }`}
                  >
                    <div className="flex items-center gap-2 font-bold">
                      {isUrgent && <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />}
                      {isWarning && <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />}
                      {isTip && <Lightbulb className="w-3.5 h-3.5 text-teal-400 shrink-0" />}
                      <span
                        className={
                          isUrgent
                            ? 'text-rose-300'
                            : isWarning
                            ? 'text-amber-300'
                            : 'text-teal-300'
                        }
                      >
                        {n.title}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-300 leading-relaxed">
                      {n.message}
                    </p>

                    {n.action && (
                      <div className="text-[10px] text-slate-400 font-medium pt-1 border-t border-slate-800/60 flex items-center gap-1">
                        <span>💡 {n.action}</span>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 bg-slate-950 border-t border-slate-800/80 text-center">
            <span className="text-[10px] text-slate-400 font-medium">
              Alerts update automatically as you log expenses
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
