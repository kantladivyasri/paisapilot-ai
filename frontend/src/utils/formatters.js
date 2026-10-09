/**
 * Utility functions for formatting Indian currency (INR), dates, and categories.
 */

export function formatINR(amount, includeDecimals = true) {
  if (amount === undefined || amount === null || isNaN(amount)) {
    return '₹0.00';
  }
  const numericVal = Number(amount);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: includeDecimals ? 2 : 0,
    maximumFractionDigits: includeDecimals ? 2 : 0,
  }).format(numericVal);
}

export function formatCompactINR(amount) {
  if (!amount || isNaN(amount)) return '₹0';
  const val = Math.abs(Number(amount));
  const sign = amount < 0 ? '-' : '';
  if (val >= 10000000) {
    return `${sign}₹${(val / 10000000).toFixed(1)}Cr`;
  }
  if (val >= 100000) {
    return `${sign}₹${(val / 100000).toFixed(1)}L`;
  }
  if (val >= 1000) {
    return `${sign}₹${(val / 1000).toFixed(1)}k`;
  }
  return `${sign}₹${val.toFixed(0)}`;
}

export function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const d = new Date(year, month, day);
      return d.toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });
    }
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? dateStr : d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export const CATEGORY_COLORS = {
  Rent: '#3B82F6',         // Blue
  Groceries: '#10B981',    // Emerald
  Food: '#F59E0B',         // Amber
  Transport: '#6366F1',    // Indigo
  Electricity: '#EAB308',  // Yellow
  Education: '#8B5CF6',    // Violet
  Shopping: '#EC4899',     // Pink
  Healthcare: '#EF4444',   // Red
  Entertainment: '#06B6D4',// Cyan
  Salary: '#10B981',       // Emerald
  Freelance: '#14B8A6',    // Teal
  Investments: '#84CC16',  // Lime
  Other: '#64748B',        // Slate
};

export function getCategoryColor(category) {
  return CATEGORY_COLORS[category] || '#64748B';
}
