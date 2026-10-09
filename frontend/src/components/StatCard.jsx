import React from 'react';
import { formatINR } from '../utils/formatters';

export default function StatCard({
  title,
  amount,
  subtitle,
  icon: Icon,
  badgeText,
  badgeType = 'neutral', // 'positive', 'negative', 'warning', 'neutral'
  isCurrency = true,
  rawSuffix = '',
}) {
  const badgeStyles = {
    positive: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    negative: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    warning: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    neutral: 'bg-slate-800 text-slate-300 border-slate-700',
  };

  const displayValue = isCurrency ? formatINR(amount) : `${amount}${rawSuffix}`;

  return (
    <div className="card-glass card-glass-hover rounded-2xl p-5 relative overflow-hidden">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          {title}
        </span>
        {Icon && (
          <div className="p-2.5 rounded-xl bg-slate-800/80 text-emerald-400 border border-slate-700/50">
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-2 mb-1.5">
        <h3 className="text-2xl font-black text-white tracking-tight">
          {displayValue}
        </h3>
      </div>

      <div className="flex items-center justify-between pt-1">
        <p className="text-xs text-slate-400">{subtitle}</p>
        {badgeText && (
          <span
            className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
              badgeStyles[badgeType] || badgeStyles.neutral
            }`}
          >
            {badgeText}
          </span>
        )}
      </div>
    </div>
  );
}
